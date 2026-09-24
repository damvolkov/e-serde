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

fn per_cell<'py>(py: Python<'py>, text: &str) -> PyResult<Bound<'py, PyAny>> {
    if text.is_empty() {
        return Ok(py.None().into_bound(py));
    }
    cell(py, text, classify(text))
}

fn row_dict<'py>(
    py: Python<'py>,
    header: &[String],
    record: &csv::StringRecord,
) -> PyResult<Bound<'py, PyAny>> {
    let row = PyDict::new(py);
    for (index, name) in header.iter().enumerate() {
        row.set_item(name, per_cell(py, &record[index])?)?;
    }
    Ok(row.into_any())
}

fn check_header(header: &[String]) -> Result<(), String> {
    if header.is_empty() {
        return Err("csv document carries no header row".to_string());
    }
    if let Some(duplicate) =
        (1..header.len()).find(|index| header[..*index].contains(&header[*index]))
    {
        return Err(format!("duplicate column name {:?}", header[duplicate]));
    }
    Ok(())
}

type Rows = Box<dyn Iterator<Item = Result<csv::StringRecord, csv::Error>> + Send + Sync>;

/// Row-at-a-time CSV iterator. The document lives in the reader (bytes or file), only
/// one record is materialized per `next`, and each cell is typed on its own — while
/// streaming there is no whole-column view, so mixed-kind columns may vary per row
/// (`loads` keeps the global polars-style inference).
#[pyclass]
struct CsvStream {
    header: Vec<String>,
    rows: Rows,
    seen: usize,
}

fn next_row<'py>(slf: &mut CsvStream, py: Python<'py>) -> PyResult<Option<Bound<'py, PyAny>>> {
    let Some(result) = slf.rows.next() else {
        return Ok(None);
    };
    slf.seen += 1;
    let record =
        result.map_err(|exc| PyValueError::new_err(format!("row {}: {exc}", slf.seen + 1)))?;
    if record.len() != slf.header.len() {
        return Err(PyValueError::new_err(format!(
            "row {} has {} fields, the header declares {}",
            slf.seen + 1,
            record.len(),
            slf.header.len()
        )));
    }
    row_dict(py, &slf.header, &record).map(Some)
}

#[pymethods]
impl CsvStream {
    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(mut slf: PyRefMut<'_, Self>) -> PyResult<Option<Bound<'_, PyAny>>> {
        let py = slf.py();
        next_row(&mut slf, py)
    }

    #[getter]
    fn header<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
        PyList::new(
            py,
            self.header
                .iter()
                .map(|name| PyString::new(py, name).into_any()),
        )
    }
}

fn stream_reader<R>(reader: csv::Reader<R>) -> Result<CsvStream, String>
where
    R: std::io::Read + Send + Sync + 'static,
{
    let mut reader = reader;
    let header: Vec<String> = reader
        .headers()
        .map_err(|exc| exc.to_string())?
        .iter()
        .map(str::to_string)
        .collect();
    check_header(&header)?;
    Ok(CsvStream {
        header,
        rows: Box::new(reader.into_records()),
        seen: 0,
    })
}

fn build_reader(bytes: Vec<u8>, delimiter: u8) -> csv::Reader<std::io::Cursor<Vec<u8>>> {
    let bytes = if bytes.starts_with(b"\xef\xbb\xbf") {
        bytes[3..].to_vec()
    } else {
        bytes
    };
    csv::ReaderBuilder::new()
        .delimiter(delimiter)
        .flexible(true)
        .trim(csv::Trim::None)
        .from_reader(std::io::Cursor::new(bytes))
}

fn stream_from(bytes: Vec<u8>, delimiter: u8) -> Result<CsvStream, String> {
    stream_reader(build_reader(bytes, delimiter))
}

fn stream_from_path(path: &str, delimiter: u8) -> Result<CsvStream, String> {
    let file = std::fs::File::open(path).map_err(|exc| format!("cannot open {path}: {exc}"))?;
    let reader = csv::ReaderBuilder::new()
        .delimiter(delimiter)
        .flexible(true)
        .trim(csv::Trim::None)
        .from_reader(std::io::BufReader::new(file));
    stream_reader(reader)
}

fn header_line(header: &[String], delimiter: u8) -> String {
    let mut out = Vec::new();
    for (index, name) in header.iter().enumerate() {
        if index > 0 {
            out.push(delimiter);
        }
        write_field(&mut out, name, delimiter);
    }
    out.push(b'\n');
    String::from_utf8(out).expect("header cells are valid utf-8")
}

fn row_line(
    header: &[String],
    row: &Bound<'_, PyAny>,
    delimiter: u8,
    number: usize,
) -> PyResult<String> {
    let dict = row
        .cast::<PyDict>()
        .map_err(|_| PyValueError::new_err(format!("record {number} is not a mapping")))?;
    if dict.len() != header.len() {
        return Err(PyValueError::new_err(format!(
            "record {number} has {} keys, the header declares {}",
            dict.len(),
            header.len()
        )));
    }
    let mut out = Vec::new();
    for (index, name) in header.iter().enumerate() {
        if index > 0 {
            out.push(delimiter);
        }
        let value = match dict.get_item(name) {
            Ok(Some(value)) => value,
            Ok(None) => {
                return Err(PyValueError::new_err(format!(
                    "record {number} is missing column {name:?}"
                )));
            }
            Err(exc) => return Err(exc),
        };
        write_cell(&mut out, &value, delimiter, number, name)?;
    }
    out.push(b'\n');
    String::from_utf8(out).map_err(|exc| PyValueError::new_err(exc.to_string()))
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
fn stream(data: Vec<u8>) -> PyResult<CsvStream> {
    stream_from(data, b',').map_err(PyValueError::new_err)
}

#[pyfunction]
fn stream_at(path: &str) -> PyResult<CsvStream> {
    stream_from_path(path, b',').map_err(PyValueError::new_err)
}

#[pyfunction]
fn dumps_header(header: Vec<String>) -> String {
    header_line(&header, b',')
}

#[pyfunction]
fn dumps_row(header: Vec<String>, number: usize, row: Bound<'_, PyAny>) -> PyResult<String> {
    row_line(&header, &row, b',', number)
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

#[pyfunction]
#[pyo3(name = "stream")]
fn stream_tsv(data: Vec<u8>) -> PyResult<CsvStream> {
    stream_from(data, b'\t').map_err(PyValueError::new_err)
}

#[pyfunction]
#[pyo3(name = "stream_at")]
fn stream_at_tsv(path: &str) -> PyResult<CsvStream> {
    stream_from_path(path, b'\t').map_err(PyValueError::new_err)
}

#[pyfunction]
#[pyo3(name = "dumps_header")]
fn dumps_header_tsv(header: Vec<String>) -> String {
    header_line(&header, b'\t')
}

#[pyfunction]
#[pyo3(name = "dumps_row")]
fn dumps_row_tsv(header: Vec<String>, number: usize, row: Bound<'_, PyAny>) -> PyResult<String> {
    row_line(&header, &row, b'\t', number)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<CsvStream>()?;
    m.add_function(wrap_pyfunction!(loads, m)?)?;
    m.add_function(wrap_pyfunction!(dumps, m)?)?;
    m.add_function(wrap_pyfunction!(stream, m)?)?;
    m.add_function(wrap_pyfunction!(stream_at, m)?)?;
    m.add_function(wrap_pyfunction!(dumps_header, m)?)?;
    m.add_function(wrap_pyfunction!(dumps_row, m)?)?;
    Ok(())
}

pub fn register_tsv(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<CsvStream>()?;
    m.add_function(wrap_pyfunction!(loads_tsv, m)?)?;
    m.add_function(wrap_pyfunction!(dumps_tsv, m)?)?;
    m.add_function(wrap_pyfunction!(stream_tsv, m)?)?;
    m.add_function(wrap_pyfunction!(stream_at_tsv, m)?)?;
    m.add_function(wrap_pyfunction!(dumps_header_tsv, m)?)?;
    m.add_function(wrap_pyfunction!(dumps_row_tsv, m)?)?;
    Ok(())
}
