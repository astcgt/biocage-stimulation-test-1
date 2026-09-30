"""Single source of truth for design, material and simulation parameters."""

H = 0.2  # voxel size (mm) = print layer height = half of 0.4 mm nozzle line width

DESIGN = dict(
    footprint_inset_mm=1.0,        # cage outline inset from vertebral body rim (rim is rounded / cortical lip)
    window_area_fraction=0.60,     # central window for the biodisc, fraction of cage footprint area
    min_wall_mm=1.2,               # >= 3 extrusion lines at 0.4 mm nozzle
    surface_smoothing_mm=0.4,      # Gaussian smoothing of STL endplate height maps (removes mesh noise)
    # tread (design B only): herringbone / chevron lugs on both bone-contact faces
    lug_height_mm=0.4,             # 2 layers at 0.2 mm
    lug_width_mm=0.8,              # 2 extrusion lines at 0.4 mm
    lug_pitch_mm=1.6,              # lug + groove
    lug_angle_deg=45.0,            # chevron arm angle to the lateral axis
    lug_edge_margin_mm=0.2,        # lugs kept off the outer/inner wall edges
    bone_slab_above_mm=70.4,       # C3 modelled from its caudal endplate up to this z (mm)
    bone_slab_below_mm=53.0,       # C4 modelled from this z up to its cranial endplate
    cortical_endplate_mm=0.4,      # bony endplate thickness
    cortical_shell_mm=0.6,         # vertebral body lateral cortical shell
)

PRINT = dict(
    process='FDM / FFF (filament extrusion), cf. Prusa i3 MK3S+ used for PLA cages in Lintz 2021 ch.4',
    filament_diameter_mm=1.75,
    nozzle_diameter_mm=0.4,
    layer_height_mm=0.2,
    line_width_mm=0.4,
    infill_percent=100,
    xy_accuracy_mm=0.1,
    nozzle_temp_C='190-210 (PLA-class lactide copolymer; tune for PLC 8516)',
    bed_temp_C='40-50',
    build_orientation='cage axis (cranio-caudal) = print Z; layers parallel to endplates',
)

MAT = dict(
    PLCL=dict(name='Corbion PURASORB PLC 8516 (85:15 L-lactide/e-caprolactone), FDM printed, 37 C',
              E=1100.0, nu=0.35,            # MPa; ESTIMATE within reported 85:15 range (~0.9-1.8 GPa)
              sigma_vm_fail=35.0,           # MPa von Mises breakage threshold (bulk ~40-45 MPa x ~0.8 FDM knock-down) ESTIMATE
              sigma_1_fail=30.0,            # MPa max principal tensile (inter-layer) breakage threshold ESTIMATE
              basquin_b=-0.085, basquin_sf=35.0,  # sigma_a = sf (2N)^b ; printed PLA-family fatigue exponent ESTIMATE
              density=1.25),
    cortical=dict(name='cortical bone / bony endplate', E=12000.0, nu=0.30),
    cancellous=dict(name='cancellous bone', E=300.0, nu=0.20),
    biodisc=dict(name='TE biodisc (collagen AF / alginate NP), Lintz 2021 ch.2 equilibrium modulus', E=0.03, nu=0.45),
)

CONTACT = dict(mu=0.30,              # PLCL-bone Coulomb friction (FEA literature 0.2 smooth PEEK / 0.5 cervical)
               penalty_factor=10.0,   # kN = factor * E_local * A_node / h (E_local = PLCL or biodisc)
               kT_ratio=0.1)          # tangential penalty kT = 0.1 kN

ENDPOINTS = dict(damage_frac=0.15, damage_report=(0.10, 0.15, 0.20), slip_mm=2.0, tilt_deg=10.0)

CYCLIC = dict(standard='ASTM F2077 (axial compression fatigue)', R=10.0, freq_hz=5.0, runout=5_000_000,
              levels=(0.25, 0.375, 0.50, 0.625, 0.75),   # Fmax as fraction of static failure load (Test 1)
              max_dD_per_jump=0.10)

SIXDOF = dict(preload_N=100.0, base_moment_Nmm=1500.0, base_shear_N=20.0, max_multiplier=10)
