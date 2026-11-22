"""Known potential sources, SW parameters, and lookup data."""

GITHUB_BASE = "https://raw.githubusercontent.com/lammps/lammps/develop/potentials/"

# Element -> list of (url, potential_type, filename) tuples
# Ordered by preference (first = best)
KNOWN_SOURCES = {
    "Cu": [
        (GITHUB_BASE + "Cu_u3.eam", "eam", "Cu_u3.eam"),
        ("https://openkim.org/download/EAM_Dynamo_GolaPastewka_2018_CuAu__MO_426403318662_000.txz", "eam", None),
    ],
    "Au": [
        (GITHUB_BASE + "Au_u3.eam", "eam", "Au_u3.eam"),
    ],
    "Ag": [
        (GITHUB_BASE + "Ag_u3.eam", "eam", "Ag_u3.eam"),
    ],
    "Al": [
        (GITHUB_BASE + "Al_jnp.eam", "eam", "Al_jnp.eam"),
        (GITHUB_BASE + "Al_mm.eam.fs", "eam", "Al_mm.eam.fs"),
        (GITHUB_BASE + "Al_zhou.eam.alloy", "eam", "Al_zhou.eam.alloy"),
    ],
    "Si": [
        (GITHUB_BASE + "Si.sw", "sw", "Si.sw"),
        (GITHUB_BASE + "SiC.tersoff", "tersoff", "SiC.tersoff"),
    ],
    "Ti": [
        ("https://openkim.org/download/EAM_Dynamo_MishinMehlPapaconstantopoulos_2004_Ti__MO_748534961139_005.txz", "eam", None),
    ],
    "Ni": [
        (GITHUB_BASE + "Ni_u3.eam", "eam", "Ni_u3.eam"),
    ],
    "Fe": [
        (GITHUB_BASE + "Fe_mm.eam.fs", "eam", "Fe_mm.eam.fs"),
    ],
    "W": [
        (GITHUB_BASE + "W_BN.eam.fs", "eam", "W_BN.eam.fs"),
    ],
    "Pt": [
        (GITHUB_BASE + "Pt_u3.eam", "eam", "Pt_u3.eam"),
    ],
}

# Known files in LAMMPS GitHub potentials directory (for pattern-based search)
GITHUB_POTENTIAL_FILES = [
    "Ag_u3.eam", "Al_jnp.eam", "Al_mm.eam.fs", "Al_zhou.eam.alloy",
    "AlCu.eam.alloy", "AlFe_mm.eam.fs", "AlO.eam",
    "Au_u3.eam", "BNC.tersoff", "Cu_u3.eam",
    "Fe_mm.eam.fs", "GaN.sw", "Ni_u3.eam",
    "Pt_u3.eam", "Si.sw", "SiC.tersoff",
    "W_BN.eam.fs",
]

# Stillinger-Weber parameters for local generation
SW_PARAMETERS = {
    "Si": {
        "epsilon": 2.1683, "sigma": 2.0951, "a": 1.80, "lambda_": 21.0,
        "gamma": 1.20, "costheta0": -0.333333333333,
        "A": 7.049556277, "B": 0.6022245584, "p": 4.0, "q": 0.0, "tol": 0.0,
        "ref": "Stillinger & Weber, Phys. Rev. B 31, 5262 (1985)",
    },
    "Ge": {
        "epsilon": 1.9321, "sigma": 2.4499, "a": 1.80, "lambda_": 31.0,
        "gamma": 1.20, "costheta0": -0.333333333333,
        "A": 7.049556277, "B": 0.6022245584, "p": 4.0, "q": 0.0, "tol": 0.0,
        "ref": "Ding & Andersen, Phys. Rev. B 34, 6987 (1986)",
    },
    "C": {
        "epsilon": 2.3890, "sigma": 1.4276, "a": 1.80, "lambda_": 100.0,
        "gamma": 1.20, "costheta0": -0.333333333333,
        "A": 7.049556277, "B": 0.6022245584, "p": 4.0, "q": 0.0, "tol": 0.0,
        "ref": "Erhart & Albe, Phys. Rev. B 71, 035211 (2005)",
    },
}

# Potential file extensions ordered by priority (higher = better match)
POTENTIAL_EXTENSIONS = {
    ".eam": 10,
    ".eam.alloy": 9,
    ".eam.fs": 8,
    ".sw": 7,
    ".tersoff": 6,
    ".meam": 5,
    ".airebo": 4,
    ".reax": 3,
    ".table": 2,
    ".dat": 1,
}

# Element name/symbol mapping for auto-detection from filenames
ELEMENT_MAP = {
    "si": "Si", "ti": "Ti", "au": "Au", "cu": "Cu", "al": "Al",
    "ni": "Ni", "fe": "Fe", "cr": "Cr", "co": "Co", "mn": "Mn",
    "w": "W", "mo": "Mo", "nb": "Nb", "ta": "Ta", "zr": "Zr",
    "ag": "Ag", "pt": "Pt", "pd": "Pd", "mg": "Mg", "ca": "Ca",
    "ge": "Ge", "c": "C", "zn": "Zn", "sn": "Sn", "pb": "Pb",
}

# Archive extensions handled by stdlib
ARCHIVE_EXTENSIONS = [".zip", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz"]
