use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use std::borrow::Cow;

use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString};

/// Column kind lattice: the empty type absorbs nothing, `Str` absorbs everything
/// non-numeric; numeric columns widen `Int → BigInt → Float` exactly like polars,
/// and a bool that meets any other kind demotes the whole column to strings.
#[derive(Clone, Copy, PartialEq, Eq)]
enum Kind {
    AllNull,
    Bool,
    Int,
    BigInt,
    Float,
    Str,
}

fn join(a: Kind, b: Kind) -> Kind {
    match (a, b) {
        (x, y) if x == y => x,
        (Kind::AllNull, y) | (y, Kind::AllNull) => y,
        (Kind::Int, Kind::BigInt) | (Kind::BigInt, Kind::Int) => Kind::BigInt,
        (Kind::Int | Kind::BigInt | Kind::Float, Kind::Float)
        | (Kind::Float, Kind::Int | Kind::BigInt) => Kind::Float,
        _ => Kind::Str,
    }
}

fn classify(text: &str) -> Kind {
    if matches!(text, "true" | "false") {
        Kind::Bool
    } else if text.parse::<i64>().is_ok() {
        Kind::Int
    } else if is_digits(text) {
        Kind::BigInt
    } else if text.parse::<f64>().is_ok() {
        Kind::Float
    } else {
        Kind::Str
    }
}

fn is_digits(text: &str) -> bool {
    let digits = text.strip_prefix(['-', '+']).unwrap_or(text);
    !digits.is_empty() && digits.bytes().all(|byte| byte.is_ascii_digit())
}

type Parsed = (Vec<String>, Vec<csv::StringRecord>, Vec<Kind>);

/// Header, records and inferred kinds — pure Rust, safe to run GIL-free.
fn parse(input: &str, delimiter: u8) -> Result<Parsed, String> {
    let input = input.trim_start_matches('\u{feff}');
    let mut reader = csv::ReaderBuilder::new()
        .delimiter(delimiter)
        .flexible(true)
        .trim(csv::Trim::None)
        .from_reader(input.as_bytes());
    let header: Vec<String> = reader
        .headers()
        .map_err(|exc| exc.to_string())?
        .iter()
        .map(str::to_string)
        .collect();
    let columns = header.len();
    if columns == 0 {
        return Err("csv document carries no header row".to_string());
    }
    if let Some(duplicate) = (1..columns).find(|index| header[..*index].contains(&header[*index])) {
        return Err(format!("duplicate column name {:?}", header[duplicate]));
    }
    let mut records = Vec::new();
    for (number, result) in reader.records().enumerate() {
        let record = result.map_err(|exc| format!("row {}: {exc}", number + 2))?;
        if record.len() != columns {
            return Err(format!(
                "row {} has {} fields, the header declares {}",
                number + 2,
                record.len(),
                columns
            ));
        }
        records.push(record);
    }
    let kinds = (0..columns)
        .map(|column| {
            records
                .iter()
                .map(|record| {
                    let value = &record[column];
                    if value.is_empty() {
                        Kind::AllNull
                    } else {
                        classify(value)
                    }
                })
                .fold(Kind::AllNull, join)
        })
        .collect();
    Ok((header, records, kinds))
}

fn cell<'py>(py: Python<'py>, text: &str, kind: Kind) -> PyResult<Bound<'py, PyAny>> {
    let value = match kind {
        Kind::AllNull => py.None().into_bound(py),
        Kind::Bool => PyBool::new(py, text == "true").to_owned().into_any(),
        Kind::Int => match text.parse::<i64>() {
            Ok(int) => int.into_pyobject(py)?.into_any(),
            Err(_) => PyString::new(py, text).into_any(),
        },
        Kind::BigInt => match text.parse::<i64>() {
            Ok(int) => int.into_pyobject(py)?.into_any(),
            Err(_) if is_digits(text) => py.import("builtins")?.getattr("int")?.call1((text,))?,
            Err(_) => PyString::new(py, text).into_any(),
        },
        Kind::Float => match text.parse::<f64>() {
            Ok(float) => float.into_pyobject(py)?.into_any(),
            Err(_) => PyString::new(py, text).into_any(),
        },
        Kind::Str => PyString::new(py, text).into_any(),
    };
    Ok(value)
}

fn build<'py>(
    py: Python<'py>,
    header: &[String],
    records: &[csv::StringRecord],
    kinds: &[Kind],
) -> PyResult<Bound<'py, PyAny>> {
    let rows = PyList::empty(py);
    for record in records {
        let row = PyDict::new(py);
        for (index, name) in header.iter().enumerate() {
            let value = &record[index];
            let item = if value.is_empty() {
                py.None().into_bound(py)
            } else {
                cell(py, value, kinds[index])?
            };
            row.set_item(name, item)?;
        }
        rows.append(row)?;
    }
    Ok(rows.into_any())
}

fn write_field(out: &mut Vec<u8>, text: &str, delimiter: u8) {
    let needs_quotes = text
        .as_bytes()
        .iter()
        .any(|byte| *byte == delimiter || matches!(byte, b'"' | b'\n' | b'\r'));
    if needs_quotes {
        out.push(b'"');
        for byte in text.as_bytes() {
            if *byte == b'"' {
                out.extend_from_slice(b"\"\"");
            } else {
                out.push(*byte);
            }
        }
        out.push(b'"');
    } else {
        out.extend_from_slice(text.as_bytes());
    }
}

fn write_cell(
    out: &mut Vec<u8>,
    value: &Bound<'_, PyAny>,
    delimiter: u8,
    row: usize,
    column: &str,
) -> PyResult<()> {
    let text: Cow<'_, str> = if value.is_none() {
        Cow::Borrowed("")
    } else if value.is_instance_of::<PyBool>() {
        Cow::Borrowed(if value.extract::<bool>()? {
            "true"
        } else {
            "false"
        })
    } else if let Ok(text) = value.extract::<Cow<'_, str>>() {
        text
    } else if value.is_instance_of::<PyInt>() || value.is_instance_of::<PyFloat>() {
        Cow::Owned(value.str()?.to_string())
    } else {
        return Err(PyTypeError::new_err(format!(
            "record {row} column {column:?} is not a csv scalar"
        )));
    };
    write_field(out, &text, delimiter);
    Ok(())
}

fn encode(py: Python<'_>, obj: Bound<'_, PyAny>, delimiter: u8) -> PyResult<String> {
    let Ok(rows) = obj.cast::<PyList>() else {
        return Err(PyValueError::new_err("csv documents are lists of records"));
    };
    let header = header_of(rows)?;
    let mut out = Vec::with_capacity(rows.len() * header.len() * 12);
    for (index, name) in header.iter().enumerate() {
        if index > 0 {
            out.push(delimiter);
        }
        write_field(&mut out, name, delimiter);
    }
    out.push(b'\n');
    let keys: Vec<Bound<'_, PyString>> =
        header.iter().map(|name| PyString::new(py, name)).collect();
    for (number, item) in rows.iter().enumerate() {
        let Ok(row) = item.cast::<PyDict>() else {
            return Err(PyValueError::new_err(format!(
                "record {} is not a mapping",
                number + 1
            )));
        };
        if row.len() != header.len() {
            return Err(PyValueError::new_err(format!(
                "record {} has {} keys, the first record declares {}",
                number + 1,
                row.len(),
                header.len()
            )));
        }
        for (index, key) in keys.iter().enumerate() {
            if index > 0 {
                out.push(delimiter);
            }
            let name = &header[index];
            let value = row.get_item(key)?.ok_or_else(|| {
                PyValueError::new_err(format!("record {} is missing column {name:?}", number + 1))
            })?;
            write_cell(&mut out, &value, delimiter, number + 1, name)?;
        }
        out.push(b'\n');
    }
    String::from_utf8(out).map_err(|exc| PyValueError::new_err(exc.to_string()))
}

fn header_of(rows: &Bound<'_, PyList>) -> PyResult<Vec<String>> {
    let Some(first) = rows.iter().next() else {
        return Err(PyValueError::new_err(
            "csv needs at least one record to derive the header",
        ));
    };
    let dict = first
        .cast::<PyDict>()
        .map_err(|_| PyValueError::new_err("csv records must be mappings"))?;
    dict.keys()
        .iter()
        .map(|key| key.extract::<String>())
        .collect::<PyResult<_>>()
}

fn loads_with<'py>(py: Python<'py>, data: &str, delimiter: u8) -> PyResult<Bound<'py, PyAny>> {
    let input = data.to_string();
    let (header, records, kinds) = py
        .detach(move || parse(&input, delimiter))
        .map_err(PyValueError::new_err)?;
    build(py, &header, &records, &kinds)
}

#[pyfunction]
fn loads<'py>(py: Python<'py>, data: &str) -> PyResult<Bound<'py, PyAny>> {
    loads_with(py, data, b',')
}

#[pyfunction]
fn dumps(py: Python<'_>, obj: Bound<'_, PyAny>) -> PyResult<String> {
    encode(py, obj, b',')
}

#[pyfunction]
#[pyo3(name = "loads")]
fn loads_tsv<'py>(py: Python<'py>, data: &str) -> PyResult<Bound<'py, PyAny>> {
    loads_with(py, data, b'\t')
}

#[pyfunction]
#[pyo3(name = "dumps")]
fn dumps_tsv(py: Python<'_>, obj: Bound<'_, PyAny>) -> PyResult<String> {
    encode(py, obj, b'\t')
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(loads, m)?)?;
    m.add_function(wrap_pyfunction!(dumps, m)?)?;
    Ok(())
}

pub fn register_tsv(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(loads_tsv, m)?)?;
    m.add_function(wrap_pyfunction!(dumps_tsv, m)?)?;
    Ok(())
}
