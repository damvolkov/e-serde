use crate::convert::{py_to_value, value_to_py};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyModule;
use saphyr::{LoadableYamlNode, Scalar, Yaml};
use serde_json::{Map, Value};

fn decode(input: &str) -> Result<Value, String> {
    let mut docs = Yaml::load_from_str(input).map_err(|exc| exc.to_string())?;
    if docs.len() != 1 {
        return Err(format!(
            "expected exactly one YAML document, found {}",
            docs.len()
        ));
    }
    yaml_to_value(docs.remove(0))
}

fn yaml_to_value(node: Yaml<'_>) -> Result<Value, String> {
    let value = match node {
        Yaml::Value(scalar) => scalar_to_value(scalar)?,
        Yaml::Representation(text, _, _) => Value::String(text.into_owned()),
        Yaml::Sequence(items) => Value::Array(
            items
                .into_iter()
                .map(yaml_to_value)
                .collect::<Result<Vec<_>, _>>()?,
        ),
        Yaml::Mapping(mapping) => {
            let mut map = Map::new();
            for (key, item) in mapping {
                map.insert(key_to_string(key)?, yaml_to_value(item)?);
            }
            Value::Object(map)
        }
        Yaml::Tagged(_, inner) => yaml_to_value(*inner)?,
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
    let pad = " ".repeat(indent);
    for (key, item) in map {
        out.push_str(&pad);
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
                emit_mapping(nested, indent + 2, out);
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
    matches!(
        text,
        "~" | "null" | "Null" | "NULL" | "true" | "True" | "TRUE" | "false" | "False" | "FALSE"
    ) || text.parse::<f64>().is_ok()
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
