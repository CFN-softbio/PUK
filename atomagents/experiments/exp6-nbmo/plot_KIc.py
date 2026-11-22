import os
import matplotlib.pyplot as plt

conc = [0, 20, 40, 60, 80, 100]

# K_Ic values in MPa*m^0.5 for each crack system (a,b,c,d) at each Nb%
sys_a = [1.275, 1.270, 1.151, 0.947, 0.656, 0.709]   # (100)[010]<001>
sys_b = [1.229, 1.212, 1.095, 0.897, 0.607, 0.680]   # (1-10)(111)<-1-12>

plt.figure(figsize=(8, 6))
plt.plot(conc, sys_a, 'o-', label='(a) [100]/(010)/<001>', linewidth=2, markersize=8)
plt.plot(conc, sys_b, 's-', label='(b) [1-10]/(111)/<-1-12>', linewidth=2, markersize=8)

plt.xlabel('Nb concentration (at.%)', fontsize=13)
plt.ylabel(r'Critical fracture toughness $K_{Ic}$ (MPa$\cdot$m$^{1/2}$)', fontsize=13)
plt.title('$K_{Ic}$ vs Nb concentration in NbMo alloys (NbMo.mtp)', fontsize=13)
plt.legend(fontsize=11, loc='best')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'KIc_vs_Nb.png'), dpi=140)
print("Saved: KIc_vs_Nb.png")
