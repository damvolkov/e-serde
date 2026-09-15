use pyo3::prelude::*;
use serde_yaml::{from_str, to_string};

#[pyfunction]
fn yaml_loads(data: &str) -> PyResult<PyObject> {
    let value: serde_yaml::Value = from_str(data)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("YAML parsing error: {}", e)))?;
    
    Python::with_gil(|py| {
        convert_yaml_value_to_py(py, &value)
    })
}

fn convert_yaml_value_to_py(py: Python, value: &serde_yaml::Value) -> PyResult<PyObject> {
    match value {
        serde_yaml::Value::Null => Ok(py.None()),
        serde_yaml::Value::Bool(b) => Ok(b.into_py(py)),
        serde_yaml::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Ok(i.into_py(py))
            } else if let Some(f) = n.as_f64() {
                Ok(f.into_py(py))
            } else {
                // For large numbers or special cases, convert to string
                Ok(n.to_string().into_py(py))
            }
        },
        serde_yaml::Value::String(s) => Ok(s.into_py(py)),
        serde_yaml::Value::Sequence(seq) => {
            let py_seq: Vec<PyObject> = seq
                .iter()
                .map(|v| convert_yaml_value_to_py(py, v))
                .collect::<Result<Vec<_>, _>>()?;
            Ok(py_seq.into_py(py))
        },
        serde_yaml::Value::Mapping(map) => {
            let dict = PyDict::new(py);
            for (k, v) in map {
                if let Some(key_str) = k.as_str() {
                    let py_value = convert_yaml_value_to_py(py, v)?;
                    dict.set_item(key_str, py_value).unwrap();
                } else {
                    // Handle non-string keys by converting to string
                    let key_str = k.to_string();
                    let py_value = convert_yaml_value_to_py(py, v)?;
                    dict.set_item(key_str, py_value).unwrap();
                }
            }
            Ok(dict.into())
        },
    }
}

#[pyfunction]
fn yaml_dumps(obj: &PyAny) -> PyResult<String> {
    // Convert Python object to YAML string
    let yaml_string = to_string(&obj)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("YAML serialization error: {}", e)))?;
    
    Ok(yaml_string)
}

#[pymodule]
fn yaml(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(yaml_loads, m)?)?;
    m.add_function(wrap_pyfunction!(yaml_dumps, m)?)?;
    Ok(())
}