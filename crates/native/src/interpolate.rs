use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyString};

/// Compose-spec variable interpolation over string leaves of a decoded tree:
/// `$VAR`, `${VAR}`, `${VAR:-default}`, `${VAR-default}`, `${VAR:?err}`,
/// `${VAR?err}`, `${VAR:+alt}`, `${VAR+alt}`, and `$$` for a literal `$`.
/// Operands are themselves interpolated, lazily. Keys are never touched.
fn expand(text: &str, env: &Bound<'_, PyDict>) -> PyResult<String> {
    let mut out = String::with_capacity(text.len());
    let mut rest = text;
    while let Some(at) = rest.find('$') {
        out.push_str(&rest[..at]);
        let tail = &rest[at + 1..];
        rest = match tail.as_bytes().first() {
            Some(b'$') => {
                out.push('$');
                &tail[1..]
            }
            Some(b'{') => {
                let close =
                    closing_brace(&tail[1..]).ok_or_else(|| invalid(text, "unterminated ${"))?;
                out.push_str(&braced(&tail[1..1 + close], text, env)?);
                &tail[2 + close..]
            }
            _ => {
                let end = name_len(tail);
                if end == 0 {
                    return Err(invalid(text, "lone $ (escape it as $$)"));
                }
                out.push_str(&lookup(env, &tail[..end])?.unwrap_or_default());
                &tail[end..]
            }
        };
    }
    out.push_str(rest);
    Ok(out)
}

fn braced(body: &str, text: &str, env: &Bound<'_, PyDict>) -> PyResult<String> {
    let end = name_len(body);
    if end == 0 {
        return Err(invalid(text, "missing variable name"));
    }
    let (name, op) = body.split_at(end);
    let value = lookup(env, name)?;
    let set = value.is_some();
    let filled = value.as_deref().is_some_and(|v| !v.is_empty());
    let (colon, op) = op.strip_prefix(':').map_or((false, op), |op| (true, op));
    let present = if colon { filled } else { set };
    let operand = op.get(1..).unwrap_or_default();
    match (op.as_bytes().first(), present) {
        (None, _) if !colon => Ok(value.unwrap_or_default()),
        (Some(b'-'), true) => Ok(value.unwrap_or_default()),
        (Some(b'-'), false) => expand(operand, env),
        (Some(b'?'), true) => Ok(value.unwrap_or_default()),
        (Some(b'?'), false) => Err(PyValueError::new_err(format!(
            "required variable {name} is missing a value: {}",
            expand(operand, env)?
        ))),
        (Some(b'+'), true) => expand(operand, env),
        (Some(b'+'), false) => Ok(String::new()),
        _ => Err(invalid(text, "unknown operator")),
    }
}

/// Index of the `}` closing a `${` whose body starts at `body`, honoring nesting.
fn closing_brace(body: &str) -> Option<usize> {
    let bytes = body.as_bytes();
    let mut depth = 0usize;
    let mut index = 0;
    while index < bytes.len() {
        match bytes[index] {
            b'$' if bytes.get(index + 1) == Some(&b'{') => {
                depth += 1;
                index += 1;
            }
            b'}' if depth == 0 => return Some(index),
            b'}' => depth -= 1,
            _ => {}
        }
        index += 1;
    }
    None
}

fn name_len(text: &str) -> usize {
    let bytes = text.as_bytes();
    match bytes.first() {
        Some(b) if b.is_ascii_alphabetic() || *b == b'_' => bytes
            .iter()
            .position(|b| !(b.is_ascii_alphanumeric() || *b == b'_'))
            .unwrap_or(bytes.len()),
        _ => 0,
    }
}

fn lookup(env: &Bound<'_, PyDict>, name: &str) -> PyResult<Option<String>> {
    env.get_item(name)?.map(|v| v.extract()).transpose()
}

fn invalid(text: &str, why: &str) -> PyErr {
    PyValueError::new_err(format!("invalid interpolation in {text:?}: {why}"))
}

fn walk<'py>(node: &Bound<'py, PyAny>, env: &Bound<'py, PyDict>) -> PyResult<Bound<'py, PyAny>> {
    let py = node.py();
    if let Ok(text) = node.cast::<PyString>() {
        let raw = text.to_str()?;
        return match raw.contains('$') {
            true => Ok(PyString::new(py, &expand(raw, env)?).into_any()),
            false => Ok(node.clone()),
        };
    }
    if let Ok(items) = node.cast::<PyList>() {
        let list = PyList::empty(py);
        for item in items {
            list.append(walk(&item, env)?)?;
        }
        return Ok(list.into_any());
    }
    if let Ok(dict) = node.cast::<PyDict>() {
        let out = PyDict::new(py);
        for (key, value) in dict {
            out.set_item(key, walk(&value, env)?)?;
        }
        return Ok(out.into_any());
    }
    Ok(node.clone())
}

#[pyfunction]
pub fn interpolate<'py>(
    tree: Bound<'py, PyAny>,
    env: Bound<'py, PyDict>,
) -> PyResult<Bound<'py, PyAny>> {
    walk(&tree, &env)
}
