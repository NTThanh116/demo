## Create and assign automatical material in Juter
## Witer: Ikeda
## Date: 2023/10/01

################################################################
############################ START #############################
################################################################
from pyjdg import *

def assign_material():
    Properties.Material.Add(
        "Structural_Steel",
        [Density([(DENSITY, 7.85e-09)]),
        Elastic([(YOUNGS_MODULUS, 200000.0),
                (POISSONS_RATIO, 0.3)])],
        iMaterialID=1
    )
    print("Completed: Created material Structural_Steel")

    # Select all part
    all_parts = JPT.GetAllParts()
    print(f"Total parts retrieved: {len(all_parts)}")

    property_id_start = 1000
    property_color = 13351846

    for idx, part in enumerate(all_parts):
        Properties.Solid(
            crlTargets=[Part(part.key)],
            strName=part.name,  
            iPropertyId=property_id_start + idx,
            iPropertyColor=property_color,
            crMaterial=Material(1),
            iCordM=-2,
            dDynaRemeshVal1=DFLT_DBL,
            dDynaRemeshVal2=DFLT_DBL,
            dDispHG=DFLT_DBL,
            iFLG=-1
        )
        print(f"Assigned material to Part '{part.name}' (ID: {part.key}) with Property ID {property_id_start + idx}")

    print("Completed: Assigned material to all visible parts")

def onGetButton1Clicked(dlg):
    assign_material()
    JPT.MessageBoxPSJ("Export successful", JPT.MsgBoxType.MB_INFORMATION_YESNOCANCEL)

def main():
    dlg = JDGCreator(title="Auto material", include_apply=False)
    dlg.add_groupbox(name="GroupBox1", text="Auto material assignment", layout="Window")

    dlg.generate_window()
    dlg.on_dlg_ok(callfunc=onGetButton1Clicked)

if __name__=='__main__':
    main()