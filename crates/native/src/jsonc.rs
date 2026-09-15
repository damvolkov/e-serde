use crate::convert::{py_to_value, value_to_py};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyModule;
use serde_json::Value;

fn decode(input: &str) -> Result<Value, String> {
    let value: Value = jsonc_parser::parse_to_serde_value(input, &Default::default())
        .map_err(|exc| exc.to_string())?;
    Ok(value)
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
    serde_json::to_string(&value).map_err(|exc| PyValueError::new_err(exc.to_string()))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(loads, m)?)?;
    m.add_function(wrap_pyfunction!(dumps, m)?)?;
    Ok(())
}
