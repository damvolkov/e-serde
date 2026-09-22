use crate::convert::{py_to_value, value_to_py};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyModule;
use saphyr::LoadableYamlNode;
use saphyr::{Scalar, Yaml};
use saphyr_parser::{BufferedInput, Event, Parser};
use serde_json::{Map, Value};
use std::collections::HashMap;

/// Cap on materialized nodes while flattening the `Rc`-shared alias graph:
/// ordinary configs are orders of magnitude below this; exponential alias
/// bombs abort on the first node past the budget instead of eating the RAM.
const NODE_BUDGET: u64 = 5_000_000;
const BUDGET_MSG: &str = "node budget exceeded (alias expansion?)";

/// Predict the materialized size from the raw event stream (aliases are single
/// events, so this scan stays linear in document text) and reject bombs before
/// saphyr materializes the graph. Slot 0 doubles as saphyr's no-anchor
/// sentinel, so its size is kept as a running maximum: the guard can
/// overestimate, never underestimate.
fn check_expansion(input: &str) -> Result<(), String> {
    let mut parser = Parser::new(BufferedInput::new(input.chars()));
    let mut anchor_size: HashMap<usize, u64> = HashMap::new();
    let mut frames: Vec<(usize, u64)> = Vec::new();
    while let Some(result) = parser.next_event() {
        let (event, _) = result.map_err(|exc| exc.to_string())?;
        match event {
            Event::DocumentStart(_) => frames.push((usize::MAX, 0)),
            Event::DocumentEnd => {
                let (_, size) = frames
                    .pop()
                    .ok_or_else(|| "unbalanced document".to_string())?;
                if size > NODE_BUDGET {
                    return Err(BUDGET_MSG.to_string());
                }
            }
            Event::Scalar(_, _, anchor, _) => {
                merge_anchor(&mut anchor_size, anchor, 1);
                add(&mut frames, 1)?;
            }
            Event::SequenceStart(anchor, _) | Event::MappingStart(anchor, _) => {
                frames.push((anchor, 1))
            }
            Event::Alias(id) => {
                let size = anchor_size.get(&id).copied().unwrap_or(1);
                add(&mut frames, size)?;
            }
            Event::SequenceEnd | Event::MappingEnd => {
                let (anchor, size) = frames
                    .pop()
                    .ok_or_else(|| "unbalanced container".to_string())?;
                merge_anchor(&mut anchor_size, anchor, size);
                add(&mut frames, size)?;
            }
            _ => {}
        }
    }
    Ok(())
}

fn merge_anchor(anchor_size: &mut HashMap<usize, u64>, anchor: usize, size: u64) {
    if anchor == usize::MAX {
        return;
    }
    let slot = anchor_size.entry(anchor).or_insert(0);
    *slot = (*slot).max(size);
}

fn add(frames: &mut [(usize, u64)], size: u64) -> Result<(), String> {
    if let Some(frame) = frames.last_mut() {
        frame.1 += size;
        if frame.1 > NODE_BUDGET {
            return Err(BUDGET_MSG.to_string());
        }
    }
    Ok(())
}

fn decode(input: &str) -> Result<Value, String> {
    check_expansion(input)?;
    let mut docs = Yaml::load_from_str(input).map_err(|exc| exc.to_string())?;
    if docs.len() != 1 {
        return Err(format!(
            "expected exactly one YAML document, found {}",
            docs.len()
        ));
    }
    let mut budget = NODE_BUDGET;
    yaml_to_value(docs.remove(0), &mut budget)
}

fn yaml_to_value(node: Yaml<'_>, budget: &mut u64) -> Result<Value, String> {
    *budget = budget
        .checked_sub(1)
        .ok_or_else(|| BUDGET_MSG.to_string())?;
    let value = match node {
        Yaml::Value(scalar) => scalar_to_value(scalar)?,
        Yaml::Representation(text, _, _) => Value::String(text.into_owned()),
        Yaml::Sequence(items) => Value::Array(
            items
                .into_iter()
                .map(|item| yaml_to_value(item, budget))
                .collect::<Result<Vec<_>, _>>()?,
        ),
        Yaml::Mapping(mapping) => {
            let mut explicit: Vec<(String, Value)> = Vec::new();
            let mut merges: Vec<Value> = Vec::new();
            for (key, item) in mapping {
                let name = key_to_string(key)?;
                let value = yaml_to_value(item, budget)?;
                if name == "<<" && matches!(value, Value::Object(_) | Value::Array(_)) {
                    merges.push(value);
                } else {
                    explicit.push((name, value));
                }
            }
            let mut map = Map::new();
            for (key, value) in explicit {
                map.insert(key, value);
            }
            for source in merges {
                apply_merge(&mut map, source);
            }
            Value::Object(map)
        }
        Yaml::Tagged(_, inner) => yaml_to_value(*inner, budget)?,
        other => return Err(format!("unsupported YAML node: {other:?}")),
    };
    Ok(value)
}

fn scalar_to_value(scalar: Scalar<'_>) -> Result<Value, String> {
    let value = match scalar {
        Scalar::Null => Value::Null,
        Scalar::Boolean(flag) => Value::Bool(flag),
        Scalar::Integer(int) => Value::from(int),
        Scalar::FloatingPoint(float) => Value::from(float.into_inner()),
        Scalar::String(text) => Value::String(text.into_owned()),
    };
    Ok(value)
}

/// YAML merge key (`<<`): explicit keys win; merged maps fill the gaps. Accepts a
/// single map or a sequence of maps (earlier entries take precedence). Non-map
/// values under `<<` are treated as literal keys upstream, so this only sees maps
/// and arrays of maps.
fn apply_merge(map: &mut Map<String, Value>, source: Value) {
    match source {
        Value::Object(obj) => {
            for (key, value) in obj {
                map.entry(key).or_insert(value);
            }
        }
        Value::Array(items) => {
            for item in items {
                apply_merge(map, item);
            }
        }
        _ => {}
    }
}

fn key_to_string(key: Yaml<'_>) -> Result<String, String> {
    let text = match key {
        Yaml::Value(Scalar::String(text)) => text.into_owned(),
        Yaml::Value(Scalar::Integer(int)) => int.to_string(),
        Yaml::Value(Scalar::Boolean(flag)) => flag.to_string(),
        Yaml::Value(Scalar::FloatingPoint(float)) => float.into_inner().to_string(),
        Yaml::Value(Scalar::Null) => "null".to_string(),
        Yaml::Representation(text, _, _) => text.into_owned(),
        other => return Err(format!("non-scalar YAML mapping key: {other:?}")),
    };
    Ok(text)
}

fn scalar_inline(value: &Value) -> Option<String> {
    let text = match value {
        Value::Null => "null".to_string(),
        Value::Bool(b) => b.to_string(),
        Value::Number(n) => n.to_string(),
        Value::String(s) => emit_token(s),
        _ => return None,
    };
    Some(text)
}

fn emit_document(value: &Value, out: &mut String) {
    match value {
        Value::Object(map) if map.is_empty() => out.push_str("{}\n"),
        Value::Array(items) if items.is_empty() => out.push_str("[]\n"),
        Value::Object(map) => emit_mapping(map, 0, out),
        Value::Array(items) => emit_sequence(items, 0, out),
        scalar => {
            out.push_str(&scalar_inline(scalar).unwrap_or_else(|| "null".to_string()));
            out.push('\n');
        }
    }
}

fn emit_mapping(map: &Map<String, Value>, indent: usize, out: &mut String) {
    emit_mapping_padded(map, indent, true, out);
}

fn emit_mapping_padded(map: &Map<String, Value>, indent: usize, pad_first: bool, out: &mut String) {
    let pad = " ".repeat(indent);
    for (position, (key, item)) in map.iter().enumerate() {
        if position > 0 || pad_first {
            out.push_str(&pad);
        }
        out.push_str(&emit_token(key));
        out.push(':');
        match item {
            Value::Object(nested) if !nested.is_empty() => {
                out.push('\n');
                emit_mapping(nested, indent + 2, out);
            }
            Value::Array(items) if !items.is_empty() => {
                out.push('\n');
                emit_sequence(items, indent, out);
            }
            Value::Object(_) => out.push_str(" {}\n"),
            Value::Array(_) => out.push_str(" []\n"),
            scalar => {
                out.push(' ');
                out.push_str(&scalar_inline(scalar).unwrap_or_default());
                out.push('\n');
            }
        }
    }
}

fn emit_sequence(items: &[Value], indent: usize, out: &mut String) {
    let pad = " ".repeat(indent);
    for item in items {
        out.push_str(&pad);
        out.push_str("- ");
        match item {
            Value::Object(nested) if !nested.is_empty() => {
                emit_mapping_padded(nested, indent + 2, false, out);
            }
            Value::Array(nested) if !nested.is_empty() => {
                emit_sequence(nested, indent + 2, out);
            }
            Value::Object(_) => out.push_str("{}\n"),
            Value::Array(_) => out.push_str("[]\n"),
            scalar => {
                out.push_str(&scalar_inline(scalar).unwrap_or_default());
                out.push('\n');
            }
        }
    }
}

fn emit_token(text: &str) -> String {
    if text_needs_quotes(text) {
        format!("{:?}", text)
    } else {
        text.to_string()
    }
}

fn text_needs_quotes(text: &str) -> bool {
    if text.is_empty() || text.trim() != text {
        return true;
    }
    if text.contains([':', '#', '\n', '"', '\''])
        || text.starts_with([
            '-', '?', '>', '|', '&', '*', '!', '%', '@', '`', '[', ']', '{', '}', ',',
        ])
    {
        return true;
    }
    if matches!(
        text,
        "~" | ".inf" | ".Inf" | ".INF" | ".nan" | ".NaN" | ".NAN"
    ) || matches!(
        text.to_ascii_lowercase().as_str(),
        "null" | "true" | "false" | "y" | "n" | "yes" | "no" | "on" | "off"
    ) {
        return true;
    }
    text.parse::<f64>().is_ok() || looks_numeric_or_date(text)
}

fn looks_numeric_or_date(text: &str) -> bool {
    if !text.starts_with(['+', '-', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']) {
        return false;
    }
    text.chars()
        .all(|c| c.is_ascii_alphanumeric() || matches!(c, '+' | '-' | '.' | '_' | ':' | ' '))
}

#[pyfunction]
fn loads<'py>(py: Python<'py>, data: &str) -> PyResult<Bound<'py, PyAny>> {
    let input = data.to_string();
    let value = py
        .detach(move || decode(&input))
        .map_err(PyValueError::new_err)?;
    value_to_py(py, value)
}

#[pyfunction]
fn dumps(obj: Bound<'_, PyAny>) -> PyResult<String> {
    let value = py_to_value(&obj)?;
    let mut out = String::new();
    emit_document(&value, &mut out);
    Ok(out)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(loads, m)?)?;
    m.add_function(wrap_pyfunction!(dumps, m)?)?;
    Ok(())
}
