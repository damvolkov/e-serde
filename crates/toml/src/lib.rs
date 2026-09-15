use pyo3::prelude::*;
use toml_edit::{de, ser};

#[pyfunction]
fn toml_loads(data: &str) -> PyResult<PyObject> {
    let value: toml_edit::Value = data.parse()
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("TOML parsing error: {}", e)))?;
    
    Python::with_gil(|py| {
        convert_toml_value_to_py(py, &value)
    })
}

fn convert_toml_value_to_py(py: Python, value: &toml_edit::Value) -> PyResult<PyObject> {
    match value {
        toml_edit::Value::String(s) => Ok(s.value().into_py(py)),
        toml_edit::Value::Integer(i) => Ok(i.value().into_py(py)),
        toml_edit::Value::Float(f) => Ok(f.value().into_py(py)),
        toml_edit::Value::Boolean(b) => Ok(b.value().into_py(py)),
        toml_edit::Value::Datetime(dt) => Ok(dt.value().to_string().into_py(py)),
        toml_edit::Value::Array(arr) => {
            let py_arr: Vec<PyObject> = arr
                .iter()
                .map(|v| convert_toml_value_to_py(py, v))
                .collect::<Result<Vec<_>, _>>()?;
            Ok(py_arr.into_py(py))
        },
        toml_edit::Value::Table(tbl) => {
            let dict = PyDict::new(py);
            for (k, v) in tbl.iter() {
                let py_value = convert_toml_value_to_py(py, v)?;
                dict.set_item(k, py_value).unwrap();
            }
            Ok(dict.into())
        },
    }
}

#[pyfunction]
fn toml_dumps(obj: &PyAny) -> PyResult<String> {
    // Convert Python object to TOML string
    let toml_string = ser::to_string(&obj)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("TOML serialization error: {}", e)))?;
    
    Ok(toml_string)
}

#[pymodule]
fn toml(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(toml_loads, m)?)?;
    m.add_function(wrap_pyfunction!(toml_dumps, m)?)?;
    Ok(())
}