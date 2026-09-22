use crate::convert::{node_to_py, py_to_node, Node};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyModule;

fn to_node(value: toml::Value) -> Node {
    match value {
        toml::Value::String(text) => Node::Str(text),
        toml::Value::Integer(int) => Node::Int(int),
        toml::Value::Float(float) => Node::Float(float),
        toml::Value::Boolean(flag) => Node::Bool(flag),
        toml::Value::Datetime(stamp) => Node::Str(stamp.to_string()),
        toml::Value::Array(items) => Node::Seq(items.into_iter().map(to_node).collect()),
        toml::Value::Table(table) => Node::Map(table.into_iter().map(|(k, v)| (k, to_node(v))).collect()),
    }
}

fn decode(input: &str) -> Result<Node, String> {
    let table: toml::Table = toml::from_str(input).map_err(|exc| exc.to_string())?;
    Ok(Node::Map(table.into_iter().map(|(k, v)| (k, to_node(v))).collect()))
}

fn from_node(node: Node) -> Result<toml::Value, String> {
    Ok(match node {
        Node::Null => return Err("TOML cannot represent null".to_string()),
        Node::Bool(flag) => toml::Value::Boolean(flag),
        Node::Int(int) => toml::Value::Integer(int),
        Node::BigInt(digits) => match digits.parse::<i64>() {
            Ok(int) => toml::Value::Integer(int),
            Err(_) => return Err(format!("TOML cannot hold the integer {digits} (beyond its 64-bit range)")),
        },
        Node::Float(float) => toml::Value::Float(float),
        Node::Str(text) => toml::Value::String(text),
        Node::Seq(items) => toml::Value::Array(items.into_iter().map(from_node).collect::<Result<_, _>>()?),
        Node::Map(entries) => {
            let mut table = toml::Table::new();
            for (key, value) in entries {
                table.insert(key, from_node(value)?);
            }
            toml::Value::Table(table)
        }
    })
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
    match from_node(node).map_err(PyValueError::new_err)? {
        toml::Value::Table(table) => {
            toml::to_string(&table).map_err(|exc| PyValueError::new_err(exc.to_string()))
        }
        _ => Err(PyValueError::new_err("TOML document root must be a table")),
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(loads, m)?)?;
    m.add_function(wrap_pyfunction!(dumps, m)?)?;
    Ok(())
}
