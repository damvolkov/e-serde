use pyo3::prelude::*;

#[pyfunction]
fn ini_loads(data: &str) -> PyResult<PyObject> {
    Python::with_gil(|py| {
        // Use Python's configparser to parse INI data
        let configparser = py.import_bound("configparser")?;
        let config_parser = configparser.getattr("ConfigParser")?;
        let parser_instance = config_parser.call0()?;
        
        // Read string data
        parser_instance.call_method1("read_string", (data,))?;
        
        // Get sections and build result dict
        let sections = parser_instance.call_method0("sections")?;
        let dict = PyDict::new(py);
        
        for section in sections.iter()? {
            let section_name = section.downcast::<PyString>()?.to_str()?;
            let section_dict = PyDict::new(py);
            
            // Get items for this section
            let items = parser_instance.call_method1("items", (section_name,))?;
            for item in items.iter()? {
                let item_tuple = item.downcast::<PyTuple>()?;
                let key = item_tuple.get_item(0)?.downcast::<PyString>()?.to_str()?;
                let value = item_tuple.get_item(1)?.downcast::<PyString>()?.to_str()?;
                section_dict.set_item(key, value)?;
            }
            
            dict.set_item(section_name, section_dict)?;
        }
        
        Ok(dict.into())
    })
}

#[pyfunction]
fn ini_dumps(obj: &PyAny) -> PyResult<String> {
    Python::with_gil(|py| {
        // Convert Python dict to INI format
        let dict = obj.downcast::<PyDict>()?;
        
        // Create a temporary ConfigParser instance and populate it
        let configparser = py.import_bound("configparser")?;
        let config_parser = configparser.getattr("ConfigParser")?;
        let parser_instance = config_parser.call0()?;
        
        // Populate sections
        for item in dict.items() {
            let key = item.get_item(0)?.downcast::<PyString>()?.to_str()?;
            let value = item.get_item(1)?;
            
            if let Ok(value_dict) = value.downcast::<PyDict>() {
                // This is a section
                for sub_item in value_dict.items() {
                    let sub_key = sub_item.get_item(0)?.downcast::<PyString>()?.to_str()?;
                    let sub_value = sub_item.get_item(1)?;
                    let sub_value_str = sub_value.str()?.to_str()?;
                    parser_instance.call_method2("set", (key, sub_key, sub_value_str))?;
                }
            }
        }
        
        // Write to string
        let output = py.import_bound("io")?.getattr("StringIO")?;
        parser_instance.call_method1("write", (output,))?;
        let result = output.call_method0("getvalue")?;
        Ok(result.downcast::<PyString>()?.to_str()?.to_string())
    })
}

#[pymodule]
fn ini(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(ini_loads, m)?)?;
    m.add_function(wrap_pyfunction!(ini_dumps, m)?)?;
    Ok(())
}