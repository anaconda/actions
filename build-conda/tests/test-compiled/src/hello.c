#define PY_SSIZE_T_CLEAN
#include <Python.h>

static PyObject *say_hello(PyObject *self, PyObject *args) {
    return PyUnicode_FromString("hello from C");
}

static PyMethodDef HelloMethods[] = {
    {"say_hello", say_hello, METH_NOARGS, "Return a hello string"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef hellomodule = {
    PyModuleDef_HEAD_INIT,
    "hello",
    NULL,
    -1,
    HelloMethods
};

PyMODINIT_FUNC PyInit_hello(void) {
    return PyModule_Create(&hellomodule);
}
