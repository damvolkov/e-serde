use pyo3::exceptions::PyTypeError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyString, PyTuple};
use serde_json::{Map, Value};

pub fn value_to_py<'py>(py: Python<'py>, value: Value) -> PyResult<Bound<'py, PyAny>> {
    let obj = match value {
        Value::Null => py.None().into_bound(py).into_any(),
        Value::Bool(b) => b.into_pyobject(py)?.to_owned().into_any(),
        Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                i.into_pyobject(py)?.into_any()
            } else if let Some(u) = n.as_u64() {
                u.into_pyobject(py)?.into_any()
            } else if let Some(f) = n.as_f64() {
                f.into_pyobject(py)?.into_any()
            } else {
                n.to_string().into_pyobject(py)?.into_any()
            }
        }
        Value::String(s) => s.into_pyobject(py)?.into_any(),
        Value::Array(items) => {
            let mut out = Vec::with_capacity(items.len());
            for item in items {
                out.push(value_to_py(py, item)?);
            }
            out.into_pyobject(py)?.into_any()
        }
        Value::Object(map) => {
            let dict = PyDict::new(py);
            for (key, item) in map {
                dict.set_item(key, value_to_py(py, item)?)?;
            }
            dict.into_any()
        }
    };
    Ok(obj)
}

pub fn py_to_value(obj: &Bound<'_, PyAny>) -> PyResult<Value> {
    if obj.is_none() {
        return Ok(Value::Null);
    }
    if obj.cast::<PyString>().is_ok() {
        return Ok(Value::String(obj.extract()?));
    }
    if let Ok(items) = obj.cast::<PyList>() {
        let out = items
            .iter()
            .map(|item| py_to_value(&item))
            .collect::<PyResult<Vec<_>>>()?;
        return Ok(Value::Array(out));
    }
    if let Ok(items) = obj.cast::<PyTuple>() {
        let out = items
            .iter()
            .map(|item| py_to_value(&item))
            .collect::<PyResult<Vec<_>>>()?;
        return Ok(Value::Array(out));
    }
    if let Ok(dict) = obj.cast::<PyDict>() {
        let mut map = Map::new();
        for (key, item) in dict {
            let name: String = key
                .extract()
                .map_err(|_| PyTypeError::new_err("config keys must be strings"))?;
            map.insert(name, py_to_value(&item)?);
        }
        return Ok(Value::Object(map));
    }
    if let Ok(flag) = obj.extract::<bool>() {
        return Ok(Value::Bool(flag));
    }
    if let Ok(int) = obj.extract::<i64>() {
        return Ok(Value::from(int));
    }
    if let Ok(uint) = obj.extract::<u64>() {
        return Ok(Value::from(uint));
    }
    if let Ok(float) = obj.extract::<f64>() {
        return Ok(Value::from(float));
    }
    Err(PyTypeError::new_err(format!(
        "cannot represent {} in a config tree",
        obj.get_type().name()?
    )))
}
