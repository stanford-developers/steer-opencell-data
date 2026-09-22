# %%
from steer_opencell_data.script_utils import build_plot_exporter

_plot_exporter = build_plot_exporter(__file__)
# %%
from steer_opencell_data.DataManager import DataManager
import steer_opencell_design as ocd
# %%
# User Inputs

#####################
# %%
import os
os.environ["OPENCELL_ENV"] = "development"
# %%
# set some standard materials

conductive_additive = ocd.ConductiveAdditive.from_database("Super P")
binder = ocd.Binder.from_database("PVDF")
insulation = ocd.InsulationMaterial.from_database("Aluminium Oxide, 95%")
separator_material = ocd.SeparatorMaterial.from_database('Polyethylene')
tape_material = ocd.TapeMaterial.from_database("Kapton")
prismatic_material = ocd.PrismaticContainerMaterial.from_database("Steel")

solid_electrolyte = ocd.Binder(
    name="Li6PS5Cl",
    density=1.9,
    specific_cost=60.0
)

solid_electrolyte_separator = ocd.SeparatorMaterial(
    name="Li6PS5Cl",
    density=1.9,
    specific_cost=60.0,
    porosity=0
)

# %%
# Create the cathode

cathode_current_collector_material = ocd.CurrentCollectorMaterial.from_database('Aluminum')

cathode_current_collector=ocd.PunchedCurrentCollector(
    material=cathode_current_collector_material,
    width=300,
    height=280,
    tab_height=30,
    tab_position=70,
    tab_width=80,
    thickness=12,
)

cathode_active_material = ocd.CathodeMaterial.from_database("NMC811")

print(f"{cathode_active_material.irreversible_specific_capacity}")

cathode_formulation = ocd.CathodeFormulation(
    active_materials={cathode_active_material: 85},
    binders={binder: 4.5, solid_electrolyte: 10},
    conductive_additives={conductive_additive: 0.5}
)

my_cathode = ocd.Cathode(
    formulation=cathode_formulation,
    current_collector=cathode_current_collector,
    calender_density=3.4,
    mass_loading=58,
)

my_cathode.porosity = 0

print(f"{my_cathode.reversible_areal_capacity}")
print(f"{my_cathode.calender_density}")

# %%
# Create the anode

cathode_current_collector_material = ocd.CurrentCollectorMaterial.from_database("Copper")

anode_current_collector = ocd.PunchedCurrentCollector(
    material=cathode_current_collector_material,
    width=300,
    height=280,
    tab_height=30,
    tab_position=230,
    tab_width=80,
    thickness=9
)

import pandas as pd

spec_cap = [0, 5000, 5000, 0]
voltage = [0, 0.001, 0.001, 0]
direction = ['charge', 'charge', 'discharge', 'discharge']

half_cell_curve = pd.DataFrame({
    'specific_capacity': spec_cap,
    'voltage': voltage,
    'direction': direction
})

lithium_metal_anode_material = ocd.AnodeMaterial(
    name="Lithium Metal",
    specific_capacity_curves=half_cell_curve,
    density=0.534,
    specific_cost=0,
    reference="Li/Li+",
    color="#C9C9C9"
)

my_anode = ocd.Anode(
    formulation=None,
    current_collector=anode_current_collector,
)
# %% [markdown]
# %%
# create the layup

separator = ocd.Separator(
    material=solid_electrolyte_separator,
    thickness=30,
    width=280,
    length=300
)

separator.areal_cost = 0.2

my_layup = ocd.ZFoldMonoLayer(
    cathode=my_cathode,
    anode=my_anode,
    separator=separator,
)

_plot_exporter.save(
    my_layup.plot_top_down_view(),
    'plot_top_down_view',
)
# %%
# create the stack assembly

my_stack = ocd.ZFoldStack(
    layup=my_layup,
    n_layers=22,
)

# looks best in safari
_plot_exporter.save(
    my_stack.plot_side_view(),
    'plot_side_view',
)
# %%
# make the electrolyte

my_electrolyte = ocd.Electrolyte(
    name="1M NaPF6 in EC:PC:DMC (1:1:1 wt%)",
    density=1.2,
    specific_cost=2.5,
    color="#FF9D00"
)
# %%
# make the encapsulation

top_laminate = ocd.LaminateSheet(
    areal_cost=0.06,
    density=1.4,
    thickness=80
)

bottom_laminate = ocd.LaminateSheet(
    areal_cost=0.06,
    density=1.4,
    thickness=80
)

cathode_terminal_connector = ocd.PouchTerminal(
    material=prismatic_material,
    width=50,
    length=10,
    thickness=1
)

anode_terminal_connector = ocd.PouchTerminal(
    material=prismatic_material,
    width=50,
    length=10,
    thickness=1
)

encapsulation = ocd.PouchEncapsulation(
    top_laminate=top_laminate,
    bottom_laminate=bottom_laminate,
    cathode_terminal=cathode_terminal_connector,
    anode_terminal=anode_terminal_connector
)
# %%
# make the cell

cell = ocd.PouchCell(
    reference_electrode_assembly=my_stack,
    electrolyte=my_electrolyte,
    electrolyte_overfill=10,
    encapsulation=encapsulation,
    n_electrode_assembly=1,
    clipped_tab_length=10,
    name='temp',
    operating_voltage_window=(2.0, 4.1),
)

# looks better in safari
_plot_exporter.save(
    cell.plot_side_view(),
    'plot_side_view',
)
_plot_exporter.save(
    cell.plot_top_down_view(),
    'plot_top_down_view',
)

# %%
_plot_exporter.save(
    cell.plot_capacity_curve(width=1300, height=800),
    'plot_capacity_curve',
)
# %%
print(f"Cost ($): {cell.cost}")
print(f"Mass (g): {cell.mass}")
print(f"Energy Density (Wh/L): {cell.volumetric_energy}")
print(f"Energy (Wh): {cell.energy}")
print(f"Energy Density (Wh/kg): {cell.specific_energy}")
print(f"Normalized Cost ($/kWh): {cell.cost_per_energy}")
