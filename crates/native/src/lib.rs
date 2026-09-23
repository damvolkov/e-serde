mod convert;
mod csv;
mod ini;
mod jsonc;
mod toml;
mod yaml;

use pyo3::prelude::*;
use pyo3::types::PyModule;

type Register = fn(&Bound<'_, PyModule>) -> PyResult<()>;

const SUBMODULES: [(&str, Register); 6] = [
    ("yaml", yaml::register),
    ("csv", csv::register),
    ("tsv", csv::register_tsv),
    ("toml", toml::register),
    ("jsonc", jsonc::register),
    ("ini", ini::register),
];

#[pymodule]
fn _native(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    for (name, register) in SUBMODULES {
        let submodule = PyModule::new(py, name)?;
        register(&submodule)?;
        m.add_submodule(&submodule)?;
    }
    Ok(())
}
