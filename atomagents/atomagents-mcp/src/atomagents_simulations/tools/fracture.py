"""Fracture toughness (critical stress intensity) tool."""

import json

import numpy as np


def critical_stress_intensity(orient_x: list, orient_y: list, orient_z: list,
                              c11: float, c12: float, c44: float,
                              gamma_s: float) -> str:
    """Compute the critical stress intensity for cleavage (KIc).

    Uses the Sih-Paris-Irwin framework for anisotropic fracture mechanics.

    Args:
        orient_x: Crack propagation direction.
        orient_y: Crack normal plane direction.
        orient_z: Crack front direction.
        c11: Elastic constant C11 in GPa.
        c12: Elastic constant C12 in GPa.
        c44: Elastic constant C44 in GPa.
        gamma_s: Surface energy in J/m^2 along the crack plane.

    Returns:
        JSON string with critical fracture toughness in MPa*m^0.5.
    """
    e1 = [1, 0, 0]
    e2 = [0., 1., 0.]
    e3 = [0, 0, 1]

    m1 = np.array(orient_x, dtype=float)
    m2 = np.array(orient_y, dtype=float)
    m3 = np.array(orient_z, dtype=float)

    m1 /= np.linalg.norm(m1)
    m2 /= np.linalg.norm(m2)
    m3 /= np.linalg.norm(m3)

    Q = np.array([
        [np.dot(m1, e1), np.dot(m1, e2), np.dot(m1, e3)],
        [np.dot(m2, e1), np.dot(m2, e2), np.dot(m2, e3)],
        [np.dot(m3, e1), np.dot(m3, e2), np.dot(m3, e3)]
    ])

    K1 = np.array([
        [Q[0, 0]**2, Q[0, 1]**2, Q[0, 2]**2],
        [Q[1, 0]**2, Q[1, 1]**2, Q[1, 2]**2],
        [Q[2, 0]**2, Q[2, 1]**2, Q[2, 2]**2]
    ])
    K2 = np.array([
        [Q[0, 1]*Q[0, 2], Q[0, 2]*Q[0, 0], Q[0, 0]*Q[0, 1]],
        [Q[1, 1]*Q[1, 2], Q[1, 2]*Q[1, 0], Q[1, 0]*Q[1, 1]],
        [Q[2, 1]*Q[2, 2], Q[2, 2]*Q[2, 0], Q[2, 0]*Q[2, 1]]
    ])
    K3 = np.array([
        [Q[1, 0]*Q[2, 0], Q[1, 1]*Q[2, 1], Q[1, 2]*Q[2, 2]],
        [Q[2, 0]*Q[0, 0], Q[2, 1]*Q[0, 1], Q[2, 2]*Q[0, 2]],
        [Q[0, 0]*Q[1, 0], Q[0, 1]*Q[1, 1], Q[0, 2]*Q[1, 2]]
    ])
    K4 = np.array([
        [Q[1, 1]*Q[2, 2]+Q[1, 2]*Q[2, 1], Q[1, 2]*Q[2, 0]+Q[1, 0]*Q[2, 2], Q[1, 0]*Q[2, 1]+Q[1, 1]*Q[2, 0]],
        [Q[2, 1]*Q[0, 2]+Q[2, 2]*Q[0, 1], Q[2, 2]*Q[0, 0]+Q[2, 0]*Q[0, 2], Q[2, 0]*Q[0, 1]+Q[2, 1]*Q[0, 0]],
        [Q[0, 1]*Q[1, 2]+Q[0, 2]*Q[1, 1], Q[0, 2]*Q[1, 0]+Q[0, 0]*Q[1, 2], Q[0, 0]*Q[1, 1]+Q[0, 1]*Q[1, 0]]
    ])

    KK1 = np.concatenate((K1, 2*K2), axis=1)
    KK2 = np.concatenate((K3, K4), axis=1)
    KK = np.concatenate((KK1, KK2), axis=0)

    C_base = np.array([
        [c11, c12, c12, 0, 0, 0],
        [c12, c11, c12, 0, 0, 0],
        [c12, c12, c11, 0, 0, 0],
        [0, 0, 0, c44, 0, 0],
        [0, 0, 0, 0, c44, 0],
        [0, 0, 0, 0, 0, c44]
    ])

    C = np.dot(np.dot(KK, C_base), np.transpose(KK))
    A1 = np.linalg.inv(C)

    b11 = (A1[0, 0]*A1[2, 2] - A1[0, 2]**2) / A1[2, 2]
    b22 = (A1[1, 1]*A1[2, 2] - A1[1, 2]**2) / A1[2, 2]
    b12 = (A1[0, 1]*A1[2, 2] - A1[0, 2]*A1[1, 2]) / A1[2, 2]
    b66 = (A1[5, 5]*A1[2, 2] - A1[1, 5]**2) / A1[2, 2]

    QQ = np.array([
        [C[0, 0], C[0, 5], C[0, 4]],
        [C[0, 5], C[5, 5], C[4, 5]],
        [C[0, 4], C[4, 5], C[4, 4]]
    ])
    R = np.array([
        [C[0, 5], C[0, 1], C[0, 3]],
        [C[5, 5], C[1, 5], C[3, 5]],
        [C[4, 5], C[1, 4], C[3, 4]]
    ])
    T = np.array([
        [C[5, 5], C[1, 5], C[3, 5]],
        [C[1, 5], C[1, 1], C[1, 3]],
        [C[3, 5], C[1, 3], C[3, 3]]
    ])

    N1 = -1 * np.dot(np.linalg.inv(T), np.transpose(R))
    N2 = np.linalg.inv(T)
    N3 = np.dot(np.dot(R, np.linalg.inv(T)), np.transpose(R)) - QQ
    NN1 = np.concatenate((N1, N2), axis=1)
    NN2 = np.concatenate((N3, np.transpose(N1)), axis=1)
    N = np.concatenate((NN1, NN2), axis=0)

    [v, u] = np.linalg.eig(N)
    a1 = [[u[0, 0]], [u[1, 0]], [u[2, 0]]]
    pp1 = v[0]
    b1 = np.dot(np.transpose(R) + np.dot(pp1, T), a1)

    a2 = [[u[0, 2]], [u[1, 2]], [u[2, 2]]]
    pp2 = v[2]
    b2 = np.dot(np.transpose(R) + np.dot(pp2, T), a2)

    a3 = [[u[0, 4]], [u[1, 4]], [u[2, 4]]]
    pp3 = v[4]
    b3 = np.dot(np.transpose(R) + np.dot(pp3, T), a3)

    AA = np.concatenate((a1, a2, a3), axis=1)
    BB = np.concatenate((b1, b2, b3), axis=1)

    L = 0.5 * np.real(1j * np.dot(AA, np.linalg.inv(BB)))
    lambda_coeff = np.linalg.inv(L)[1, 1]
    K_GG = np.sqrt(2 * gamma_s * lambda_coeff * 10**9) * 10**(-6)

    output_dict = {
        'Critical fracture toughness (MPa*m^1/2)': f'{K_GG:.3f}',
    }

    return json.dumps(output_dict)
