use pyo3::exceptions::PyTypeError;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString, PyTuple};

/// Lossless config tree. `serde_json::Value` is the wrong intermediate for this
/// library: it collapses non-finite floats to `null` and integers past u64 to
/// imprecise doubles. `Node` keeps every scalar exactly as its source had it.
pub enum Node {
    Null,
    Bool(bool),
    /// Integer that fits the canonical i64 (the common case).
    Int(i64),
    /// Integer beyond i64/u64, kept as exact decimal text.
    BigInt(String),
    /// Any double, including `inf`/`-inf`/`nan` (each format decides whether to emit them).
    Float(f64),
    Str(String),
    Seq(Vec<Node>),
    Map(Vec<(String, Node)>),
}

fn bigint_to_py<'py>(py: Python<'py>, digits: &str) -> PyResult<Bound<'py, PyAny>> {
    py.import("builtins")?.getattr("int")?.call1((digits,))
}

pub fn node_to_py<'py>(py: Python<'py>, node: Node) -> PyResult<Bound<'py, PyAny>> {
    let obj = match node {
        Node::Null => py.None().into_bound(py),
        Node::Bool(b) => PyBool::new(py, b).to_owned().into_any(),
        Node::Int(i) => i.into_pyobject(py)?.into_any(),
        Node::BigInt(digits) => bigint_to_py(py, &digits)?,
        Node::Float(f) => f.into_pyobject(py)?.into_any(),
        Node::Str(s) => s.into_pyobject(py)?.into_any(),
        Node::Seq(items) => {
            let list = PyList::empty(py);
            for item in items {
                list.append(node_to_py(py, item)?)?;
            }
            list.into_any()
        }
        Node::Map(entries) => {
            let dict = PyDict::new(py);
            for (key, value) in entries {
                dict.set_item(key, node_to_py(py, value)?)?;
            }
            dict.into_any()
        }
    };
    Ok(obj)
}

pub fn py_to_node(obj: &Bound<'_, PyAny>) -> PyResult<Node> {
    if obj.is_none() {
        return Ok(Node::Null);
    }
    if obj.is_instance_of::<PyBool>() {
        return Ok(Node::Bool(obj.extract::<bool>()?));
    }
    if let Ok(text) = obj.cast::<PyString>() {
        return Ok(Node::Str(text.extract()?));
    }
    if obj.is_instance_of::<PyInt>() {
        return match obj.extract::<i64>() {
            Ok(int) => Ok(Node::Int(int)),
            Err(_) => Ok(Node::BigInt(obj.str()?.to_string())),
        };
    }
    if let Ok(float) = obj.cast::<PyFloat>() {
        return Ok(Node::Float(float.value()));
    }
    if let Ok(items) = obj.cast::<PyList>() {
        return sequence_to_node(items.iter());
    }
    if let Ok(items) = obj.cast::<PyTuple>() {
        return sequence_to_node(items.iter());
    }
    if let Ok(dict) = obj.cast::<PyDict>() {
        let mut entries = Vec::with_capacity(dict.len());
        for (key, value) in dict {
            let name = key
                .extract::<String>()
                .map_err(|_| PyTypeError::new_err("config keys must be strings"))?;
            entries.push((name, py_to_node(&value)?));
        }
        return Ok(Node::Map(entries));
    }
    Err(PyTypeError::new_err(format!(
        "cannot represent {} in a config tree",
        obj.get_type().name()?
    )))
}

fn sequence_to_node<'a>(items: impl Iterator<Item = Bound<'a, PyAny>>) -> PyResult<Node> {
    items
        .map(|item| py_to_node(&item))
        .collect::<PyResult<Vec<_>>>()
        .map(Node::Seq)
}

pub fn to_json_string(node: &Node) -> String {
    let mut out = String::new();
    write_json(node, &mut out);
    out
}

fn write_json(node: &Node, out: &mut String) {
    match node {
        Node::Null => out.push_str("null"),
        Node::Bool(true) => out.push_str("true"),
        Node::Bool(false) => out.push_str("false"),
        Node::Int(i) => out.push_str(&i.to_string()),
        Node::BigInt(digits) => out.push_str(digits),
        Node::Float(f) => out.push_str(&json_float(*f)),
        Node::Str(s) => write_json_str(s, out),
        Node::Seq(items) => {
            out.push('[');
            for (index, item) in items.iter().enumerate() {
                if index > 0 {
                    out.push(',');
                }
                write_json(item, out);
            }
            out.push(']');
        }
        Node::Map(entries) => {
            out.push('{');
            for (index, (key, value)) in entries.iter().enumerate() {
                if index > 0 {
                    out.push(',');
                }
                write_json_str(key, out);
                out.push(':');
                write_json(value, out);
            }
            out.push('}');
        }
    }
}

fn json_float(value: f64) -> String {
    if value.is_finite() {
        return serde_json::Number::from_f64(value).map_or_else(String::new, |n| n.to_string());
    }
    String::from("null")
}

fn write_json_str(text: &str, out: &mut String) {
    out.push('"');
    for ch in text.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{08}' => out.push_str("\\b"),
            '\u{0c}' => out.push_str("\\f"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
}
