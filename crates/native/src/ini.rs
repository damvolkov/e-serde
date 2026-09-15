use ini::Ini;
use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyModule};

type Sections = Vec<(String, Vec<(String, String)>)>;

fn decode(input: &str) -> Result<Sections, String> {
    let conf = Ini::load_from_str(input).map_err(|exc| exc.to_string())?;
    let mut sections: Sections = Vec::new();
    for (name, props) in conf.iter() {
        if props.iter().next().is_none() {
            continue;
        }
        let Some(section) = name else {
            return Err("keys found outside of any section".to_string());
        };
        let items = props
            .iter()
            .map(|(key, value)| (key.to_string(), value.to_string()))
            .collect();
        sections.push((section.to_string(), items));
    }
    Ok(sections)
}

fn scalar_to_text(value: &Bound<'_, PyAny>) -> PyResult<String> {
    let text = if let Ok(flag) = value.extract::<bool>() {
        flag.to_string()
    } else if let Ok(int) = value.extract::<i64>() {
        int.to_string()
    } else if let Ok(float) = value.extract::<f64>() {
        float.to_string()
    } else if let Ok(text) = value.extract::<String>() {
        text
    } else {
        return Err(PyTypeError::new_err(
            "INI values must be str, int, float or bool",
        ));
    };
    Ok(text)
}

fn encode(obj: &Bound<'_, PyAny>) -> Result<String, PyErr> {
    let dict = obj
        .cast::<PyDict>()
        .map_err(|_| PyTypeError::new_err("INI dumps expects a mapping of sections to mappings"))?;
    let mut out = String::new();
    for (section, items) in dict {
        let name: String = section
            .extract()
            .map_err(|_| PyTypeError::new_err("section names must be str"))?;
        let body = items
            .cast::<PyDict>()
            .map_err(|_| PyTypeError::new_err(format!("section {name:?} must be a mapping")))?;
        out.push_str(&format!("[{name}]\n"));
        for (key, value) in body {
            let option: String = key
                .extract()
                .map_err(|_| PyTypeError::new_err("option names must be str"))?;
            let text = scalar_to_text(&value)?;
            let escaped = text.replace('\\', "\\\\").replace('\n', "\\n");
            out.push_str(&format!("{option} = {escaped}\n"));
        }
        out.push('\n');
    }
    Ok(out)
}

#[pyfunction]
fn loads<'py>(py: Python<'py>, data: &str) -> PyResult<Bound<'py, PyAny>> {
    let input = data.to_string();
    let sections = py
        .detach(move || decode(&input))
        .map_err(PyValueError::new_err)?;
    let dict = PyDict::new(py);
    for (section, items) in sections {
        let body = PyDict::new(py);
        for (key, value) in items {
            body.set_item(key, value)?;
        }
        dict.set_item(section, body)?;
    }
    Ok(dict.into_any())
}

#[pyfunction]
fn dumps(obj: Bound<'_, PyAny>) -> PyResult<String> {
    encode(&obj)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(loads, m)?)?;
    m.add_function(wrap_pyfunction!(dumps, m)?)?;
    Ok(())
}
