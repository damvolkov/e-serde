use crate::convert::{node_to_py, py_to_node, to_json_string, Node};
use jsonc_parser::{parse_to_value, JsonValue};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyModule;

/// `jsonc-parser` yields numbers as raw text; classify int vs float so a
/// 200-digit integer survives as a BigInt instead of collapsing to f64.
fn to_node(value: JsonValue<'_>) -> Node {
    match value {
        JsonValue::Null => Node::Null,
        JsonValue::Boolean(flag) => Node::Bool(flag),
        JsonValue::String(text) => Node::Str(text.into_owned()),
        JsonValue::Number(raw) => classify_number(raw),
        JsonValue::Array(items) => Node::Seq(items.into_iter().map(to_node).collect()),
        JsonValue::Object(object) => Node::Map(
            object
                .into_iter()
                .map(|(key, item)| (key.into_owned(), to_node(item)))
                .collect(),
        ),
    }
}

fn classify_number(raw: &str) -> Node {
    if raw.contains(['.', 'e', 'E']) {
        return Node::Float(raw.parse().unwrap_or(f64::NAN));
    }
    match raw.parse::<i64>() {
        Ok(int) => Node::Int(int),
        Err(_) => Node::BigInt(raw.to_string()),
    }
}

fn decode(input: &str) -> Result<Node, String> {
    match parse_to_value(input, &Default::default()).map_err(|exc| exc.to_string())? {
        Some(value) => Ok(to_node(value)),
        None => Err("jsonc document is empty".to_string()),
    }
}

#[pyfunction]
fn loads<'py>(py: Python<'py>, data: &str) -> PyResult<Bound<'py, PyAny>> {
    let input = data.to_string();
    let node = py
        .detach(move || decode(&input))
        .map_err(PyValueError::new_err)?;
    node_to_py(py, node)
}

#[pyfunction]
fn dumps(obj: Bound<'_, PyAny>) -> PyResult<String> {
    let node = py_to_node(&obj)?;
    Ok(to_json_string(&node))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(loads, m)?)?;
    m.add_function(wrap_pyfunction!(dumps, m)?)?;
    Ok(())
}
