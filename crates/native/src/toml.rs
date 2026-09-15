use crate::convert::{py_to_value, value_to_py};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyModule;
use serde_json::{Map, Value};

fn toml_to_json(scalar: toml::Value) -> Value {
    match scalar {
        toml::Value::String(text) => Value::String(text),
        toml::Value::Integer(int) => Value::from(int),
        toml::Value::Float(float) => Value::from(float),
        toml::Value::Boolean(flag) => Value::Bool(flag),
        toml::Value::Datetime(stamp) => Value::String(stamp.to_string()),
        toml::Value::Array(items) => Value::Array(items.into_iter().map(toml_to_json).collect()),
        toml::Value::Table(table) => Value::Object(table_to_map(table)),
    }
}

fn table_to_map(table: toml::Table) -> Map<String, Value> {
    table
        .into_iter()
        .map(|(key, item)| (key, toml_to_json(item)))
        .collect()
}

fn decode(input: &str) -> Result<Value, String> {
    let table: toml::Table = toml::from_str(input).map_err(|exc| exc.to_string())?;
    Ok(Value::Object(table_to_map(table)))
}

fn toml_to_string(value: &Value) -> Result<toml::Value, String> {
    let converted = match value {
        Value::Null => return Err("TOML cannot represent null".to_string()),
        Value::Bool(b) => toml::Value::Boolean(*b),
        Value::Number(n) => {
            if let Some(int) = n.as_i64() {
                toml::Value::Integer(int)
            } else if let Some(uint) = n.as_u64() {
                match i64::try_from(uint) {
                    Ok(int) => toml::Value::Integer(int),
                    Err(_) => toml::Value::Float(uint as f64),
                }
            } else if let Some(float) = n.as_f64() {
                toml::Value::Float(float)
            } else {
                return Err(format!("unsupported TOML number: {n}"));
            }
        }
        Value::String(s) => toml::Value::String(s.clone()),
        Value::Array(items) => toml::Value::Array(
            items
                .iter()
                .map(toml_to_string)
                .collect::<Result<Vec<_>, _>>()?,
        ),
        Value::Object(map) => {
            let table = map
                .iter()
                .map(|(key, item)| Ok((key.clone(), toml_to_string(item)?)))
                .collect::<Result<toml::Table, String>>()?;
            toml::Value::Table(table)
        }
    };
    Ok(converted)
}

fn encode(value: &Value) -> Result<String, String> {
    if !value.is_object() {
        return Err("TOML top level must be a mapping".to_string());
    }
    let converted = toml_to_string(value)?;
    toml::to_string_pretty(&converted).map_err(|exc| exc.to_string())
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
    encode(&value).map_err(PyValueError::new_err)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(loads, m)?)?;
    m.add_function(wrap_pyfunction!(dumps, m)?)?;
    Ok(())
}
