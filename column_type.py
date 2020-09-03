import csv
import FreeCAD
import Part
import Arch
import Draft
from FreeCAD import Base
from section import make_section, create_ipe, create_plate
from columnTypeFunctions import (decompose_section_name, remove_obj,
                                find_empty_levels, find_nardebani_plate_levels)
from os.path import join, dirname, abspath

class ColumnType:
    def __init__(self, obj):
        obj.Proxy = self
        self.set_properties(obj)

    def set_properties(self, obj):
        self.Type = "ColumnType"

        # if not hasattr(obj, "n"):
        #     obj.addProperty(
        #         "App::PropertyEnumeration",
        #         "n",
        #         "IPE",
        #         )
        #     obj.n = ['2', '3']

        if not hasattr(obj, "size"):
            obj.addProperty(
                "App::PropertyEnumeration",
                "size",
                "IPE",
                )
            obj.size = ["14", "16", "18", "20", "22", "24", "27", "30"]

        if not hasattr(obj, "pa_baz"):
            obj.addProperty(
                "App::PropertyBool",
                "pa_baz",
                "IPE",
                )

        if not hasattr(obj, "Placement"):
            obj.addProperty(
                "App::PropertyPlacement",
                "Placement",
                "Base",
                )
        
        if not hasattr(obj, "heights"):
            obj.addProperty(
                "App::PropertyFloatList",
                "heights",
                "column_type",
            )

        if not hasattr(obj, "base_level"):
            obj.addProperty(
                "App::PropertyFloat",
                "base_level",
                "column_type",
            )

        if not hasattr(obj, "childrens_name"):
            obj.addProperty(
                "App::PropertyStringList",
                "childrens_name",
                "column_type",
                )
        obj.setEditorMode("childrens_name", 1)

        if not hasattr(obj, "sections_name"):
            obj.addProperty(
                "App::PropertyStringList",
                "sections_name",
                "column_type",
            )

        if not hasattr(obj, "extend_length"):
            obj.addProperty(
                "App::PropertyFloat",
                "extend_length",
                "column_type",
                )

        if not hasattr(obj, "profile"):
            obj.addProperty(
                "App::PropertyLink",
                "profile",
                "IPE",
                )

        if not hasattr(obj, "v_scale"):
            obj.addProperty(
                "App::PropertyFloat",
                "v_scale",
                "column_type",
                ).v_scale = .5

        if not hasattr(obj, "composite_deck"):
            obj.addProperty(
                "App::PropertyBool",
                "composite_deck",
                "Deck",
                ).composite_deck = True


    def execute(self, obj):
        scale = 1000 * obj.v_scale
        # shapes = []
        levels = [obj.base_level]
        for height in obj.heights:
            levels.append(levels[-1] + height)

        simplify_sections_name = [obj.sections_name[0]]
        simplify_levels =[obj.base_level * scale]
        for i, section_name in enumerate(obj.sections_name):
            if section_name != simplify_sections_name[-1]:
                simplify_sections_name.append(section_name)
                simplify_levels.append((levels[i] + obj.extend_length) * scale)
        simplify_levels.append((levels[-1] + obj.extend_length) * scale)


        merge_flang_plates = []
        merge_flang_levels = [simplify_levels[0]]
        merge_web_plates = []
        merge_web_levels = [simplify_levels[0]]
        souble_ipes = []
        souble_ipe_levels = [simplify_levels[0]]

        for i, name in enumerate(simplify_sections_name):
            n, _, flang_plate, web_plate = decompose_section_name(name)
            if flang_plate or (i == len(simplify_sections_name) - 1):
                extend_button_flang_length = 0
            else:
                extend_button_flang_length = -2 * obj.extend_length * scale

            level = simplify_levels[i + 1] + extend_button_flang_length
            if merge_flang_plates:
                if flang_plate != merge_flang_plates[-1]:
                    merge_flang_plates.append(flang_plate)
                    merge_flang_levels.append(level)
                else:
                    merge_flang_levels[-1] = level
            else:
                merge_flang_plates.append(flang_plate)
                merge_flang_levels.append(level)
            

            if web_plate:
                extend_button_web_length = 0
            else:
                extend_button_web_length = -2 * obj.extend_length * scale

            level = simplify_levels[i + 1] + extend_button_web_length
            if merge_web_plates:
                if web_plate != merge_web_plates[-1]:
                    merge_web_plates.append(web_plate)
                    merge_web_levels.append(level)
                else:
                    merge_web_levels[-1] = level
            else:
                merge_web_plates.append(web_plate)
                merge_web_levels.append(level)

            
            if n == 3 or (i == len(simplify_sections_name) - 1):
                extend_button_ipe_length = 0
            else:
                extend_button_ipe_length = -2 * obj.extend_length * scale

            level = simplify_levels[i + 1] + extend_button_ipe_length
            if souble_ipes:
                if n != souble_ipes[-1]:
                    souble_ipes.append(n)
                    souble_ipe_levels.append(level)
                else:
                    souble_ipe_levels[-1] = level
            else:
                souble_ipes.append(n)
                souble_ipe_levels.append(level)

        # create main IPE structures
        ipe_shapes, bf, d, tf, tw = self.make_profile(obj)
        ipe = ipe_shapes[0]
        ipe_section_obj = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "ipe_section")
        ipe_section_obj.Shape = Part.makeCompound(ipe_shapes)
        IPE = Arch.makeStructure(ipe_section_obj, name="IPE")
        h = simplify_levels[-1] - simplify_levels[0]
        IPE.Height = h
        IPE.Placement.Base = FreeCAD.Vector(0, 0, simplify_levels[0]) + obj.Placement.Base
        IPE.ViewObject.ShapeColor = (1.0, 0.0, 0.0)

        # souble ipe creation
        souble_ipe_names = []
        souble_ipe_section = ipe.copy()
        for i, n in enumerate(souble_ipes):
            if n == 3:
                souble_ipe_section.Placement.Base = FreeCAD.Vector(0, 0, souble_ipe_levels[i]) + obj.Placement.Base
                souble_ipe_section_obj = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "ipe")
                souble_ipe_section_obj.Shape = souble_ipe_section
                souble_ipe_obj = Arch.makeStructure(souble_ipe_section_obj, name="IPE")
                h = souble_ipe_levels[i + 1] - souble_ipe_levels[i]
                souble_ipe_obj.Height = h
                souble_ipe_obj.ViewObject.ShapeColor = (.80, 0.0, 0.0)
                souble_ipe_names.append(souble_ipe_obj.Name)

        flang_plate_names = []
        connection_ipes = []
        neshiman_levels = []
        neshiman_obj_names = []
        step_file = join(dirname(abspath(__file__)),"shapes", "neshiman.step")
        if obj.composite_deck:
            neshiman_base_z = 0
        else:
            neshiman_base_z = 100 * obj.v_scale
        
        import ImportGui


        for i, plate in enumerate(merge_flang_plates):
            if plate:
                width = plate[0]
                height = plate[1]
                y = (d + height) / 2
                plt = create_plate(width, height)
                plt.Placement.Base = FreeCAD.Vector(0, y, merge_flang_levels[i]) + obj.Placement.Base
                plb = plt.copy()
                plb.Placement.Base = FreeCAD.Vector(0, -y, merge_flang_levels[i]) + obj.Placement.Base
                palte_obj = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "Flang_Plate")
                palte_obj.Shape = Part.makeCompound([plt, plb])
                PLATE = Arch.makeStructure(palte_obj)
                h = merge_flang_levels[i + 1] - merge_flang_levels[i]
                PLATE.Height = h
                PLATE.ViewObject.ShapeColor = (0.0, 0.0, 1.0)
                flang_plate_names.append(PLATE.Name)
                # create neshimans
                for lev in levels[1:]:
                    if merge_flang_levels[i] < lev * scale < merge_flang_levels[i + 1]:
                        y = - (d / 2 + height)
                        z = lev * scale + neshiman_base_z

                        document = FreeCAD.ActiveDocument
                        current_instances = set(document.findObjects())
                        ImportGui.insert(step_file, document.Name)
                        new_instances = set(document.findObjects()) - current_instances
                        o = new_instances.pop()
                        o.Placement.Base = FreeCAD.Vector(0, y, z) + obj.Placement.Base
                        o.ViewObject.ShapeColor = (1.0, 1.0, 0.0)
                        Draft.scale(o, FreeCAD.Vector(1, 1, obj.v_scale), copy=False)
                        neshiman_obj_names.append(o.Name)
                        neshiman_levels.append(lev)

        if obj.pa_baz:
            flangs_and_3ipes = flang_plate_names + souble_ipe_names
            empty_levels = find_empty_levels(flangs_and_3ipes, levels, scale)
            print(f"empty_levels = {empty_levels}")
            if empty_levels:
                connection_ipe_section = ipe.copy()
                for lev in empty_levels:
                    connection_ipe_section.Placement.Base = IPE.Placement.Base
                    if lev != simplify_levels[0]:
                        connection_ipe_section.Placement.Base.z = lev - .5 * scale


                    connection_ipe_section_obj = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "ipe")
                    connection_ipe_section_obj.Shape = connection_ipe_section
                    connection_ipe_obj = Arch.makeStructure(connection_ipe_section_obj)
                    connection_ipe_obj.Height = 1 * scale
                    connection_ipe_obj.ViewObject.ShapeColor = (.80, 0.0, 0.0)
                    connection_ipes.append(connection_ipe_obj.Name)
                # for lev in levels[1:]:
                #     for tmp_level in empty_levels:
                #         if tmp_level[0] < lev  * scale < tmp_level[1]:
                #             connection_ipe_section_obj = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "ipe")
                #             connection_ipe_section_obj.Shape = connection_ipe_section
                #             connection_ipe_obj = Arch.makeStructure(connection_ipe_section_obj)
                #             connection_ipe_obj.Height = 1 * scale
                #             connection_ipe_obj.ViewObject.ShapeColor = (.80, 0.0, 0.0)
                #             connection_ipes.append(connection_ipe_obj.Name)


        # draw plate for pa_baz column (nardebani)
            nardebani_levels = find_nardebani_plate_levels(connection_ipes, flangs_and_3ipes)
            bb = ipe_section_obj.Shape.BoundBox
            width = bb.XLength - bf / 2
            height = 5
            y = (d + height) / 2
            # flangs_and_ipes = connection_ipes + flang_plate_names
            # flangs_and_ipes = sorted(flangs_and_ipes, key=lambda name: FreeCAD.ActiveDocument.getObject(name).Base.Shape.BoundBox.ZMin)
            # for i in range(len(flangs_and_ipes) - 1):
            #     o1 = FreeCAD.ActiveDocument.getObject(flangs_and_ipes[i])
            #     o2 = FreeCAD.ActiveDocument.getObject(flangs_and_ipes[i + 1])
            #     z1 = o1.Base.Shape.BoundBox.ZMax + o1.Height.Value 
            #     z2 = o2.Base.Shape.BoundBox.ZMin
            for lev in nardebani_levels:
                z1 = lev[0] + .2 * scale
                z2 = lev[1]
                h = z2 - z1
                if h > 0:
                    space = .4 * scale # constant
                    n_z = int(h / space)
                    plt = create_plate(width, height)
                    plt.Placement.Base = FreeCAD.Vector(0, y, z1) + obj.Placement.Base
                    plb = plt.copy()
                    plb.Placement.Base = FreeCAD.Vector(0, -y, z1) + obj.Placement.Base
                    palte_obj = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "Flang_Plate")
                    palte_obj.Shape = Part.makeCompound([plt, plb])
                    PLATE = Arch.makeStructure(palte_obj)
                    PLATE.Height = .15 * scale
                    PLATE.ViewObject.ShapeColor = (0.0, 0.0, 1.0)
                    _obj_ = Draft.make_ortho_array(PLATE, v_z=FreeCAD.Vector(0.0, 0.0, space), n_x=1, n_y=1, n_z=n_z)
                    flang_plate_names.append(_obj_.Name)

        for lev in levels[1:]:
            if lev not in neshiman_levels:
                # if obj.pa_baz:
                #     y = - (d / 2 + height)
                # else:
                y = - d / 2
                z = lev * scale + neshiman_base_z
                document = FreeCAD.ActiveDocument
                current_instances = set(document.findObjects())
                ImportGui.insert(step_file, document.Name)
                new_instances = set(document.findObjects()) - current_instances
                o = new_instances.pop()
                o.Placement.Base = FreeCAD.Vector(0, y, z) + obj.Placement.Base
                o.ViewObject.ShapeColor = (1.0, 1.0, 0.0)
                Draft.scale(o, FreeCAD.Vector(1, 1, obj.v_scale), copy=False)
                neshiman_obj_names.append(o.Name)
                neshiman_levels.append(lev)

        web_plate_names = []
        for i, plate in enumerate(merge_web_plates):
            if plate:
                width = plate[0]
                height = plate[1]
                x = ipe.Placement.Base.x + (tw + height) / 2
                plwr = create_plate(height, width)
                plwr.Placement.Base = FreeCAD.Vector(x, 0, merge_web_levels[i]) + obj.Placement.Base
                plwl = plwr.copy(False)
                plwl.Placement.Base = FreeCAD.Vector(-x, 0, merge_web_levels[i]) + obj.Placement.Base
                palte_obj = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "web_Plate")
                palte_obj.Shape = Part.makeCompound([plwr, plwl])
                PLATE = Arch.makeStructure(palte_obj)
                h = merge_web_levels[i + 1] - merge_web_levels[i]
                PLATE.Height = h
                PLATE.ViewObject.ShapeColor = (0.0, 1.0, 0.0)
                web_plate_names.append(PLATE.Name)

        #  insert BASE PLATE
        h = .02 * scale
        length = 700
        base_plate = Arch.makeStructure(length=length, width=length, height= h, name='BasePlate')
        x = obj.Placement.Base.x - length / 2
        y = obj.Placement.Base.y
        z = obj.base_level * scale - h / 2 
        base_plate.Placement.Base = FreeCAD.Vector(x, y, z)
        base_plate.ViewObject.ShapeColor = (1.0, 0.0, 0.0)

        childrens_name = flang_plate_names + web_plate_names + [IPE.Name] + \
                        [base_plate.Name] + connection_ipes + neshiman_obj_names + souble_ipe_names
        old_childrens_name = obj.childrens_name
        obj.childrens_name = childrens_name
        for name in old_childrens_name:
            remove_obj(name)
        obj.childrens_name = childrens_name

    


    def make_profile(self, obj):
        shapes = []
        sectionSize = int(obj.size)
        sectionType = "IPE"
        file_name = "Section_IPE.csv"
        with open(join(dirname(abspath(__file__)),"table",file_name),'r') as f:
            reader=csv.DictReader(f,delimiter=';')
            for row in reader:
                if row['SSIZE'] == f"IPE{sectionSize * 10}":
                    bf = float(row["BF"])
                    d = float(row["D"])
                    tw = float(row["TW"])
                    tf = float(row["TF"])
                    break

        if obj.pa_baz:
            dist = bf
        else:
            dist = 0

        ipe = create_ipe(bf, d, tw, tf)
        deltax = bf + dist
        ipe.Placement.Base.x = deltax / 2
        ipe2 = ipe.copy()
        ipe2.Placement.Base.x = -deltax / 2
        shapes.extend([ipe, ipe2])

        return shapes, bf, d, tf, tw


class ViewProviderColumnType:
    def __init__(self, obj):
        ''' Set this object to the proxy object of the actual view provider '''
        obj.Proxy = self

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object

    def updateData(self, fp, prop):
        ''' If a property of the handled feature has changed we have the chance to handle this here '''
        return

    def getDisplayModes(self, obj):
        ''' Return a list of display modes. '''
        modes = []
        return modes

    def getDefaultDisplayMode(self):
        ''' Return the name of the default display mode. It must be defined in getDisplayModes. '''
        return "Shaded"

    def setDisplayMode(self, mode):
        ''' Map the display mode defined in attach with those defined in getDisplayModes.
        Since they have the same names nothing needs to be done. This method is optional.
        '''
        return mode

    def onChanged(self, vp, prop):
        ''' Print the name of the property that has changed '''
        FreeCAD.Console.PrintMessage("Change View property: " + str(prop) + "\n")

    def claimChildren(self):
        children=[FreeCAD.ActiveDocument.getObject(name) for name in self.Object.childrens_name]
        return children

    def getIcon(self):
        return join(dirname(abspath(__file__)),"icons","column_types")





def make_column_type(heights, sections_name, size=16, pa_baz=False, base_level=0, extend_length=1.2, pos=(0, 0)):
    '''

    '''
    obj = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "column_type")
    ColumnType(obj)
    ViewProviderColumnType(obj.ViewObject)
    obj.heights = heights
    obj.sections_name = sections_name
    obj.base_level = base_level
    obj.extend_length = extend_length
    position = FreeCAD.Vector(pos[0], pos[1], 0)
    obj.Placement.Base = position
    # obj.n = str(n)
    obj.size = str(size)
    obj.pa_baz = pa_baz
    FreeCAD.ActiveDocument.recompute()
    FreeCAD.ActiveDocument.recompute()
    return obj

if __name__ == '__main__':
    make_column_type([4, 3.2, 3.2, 3.2, 3.3, 5], ['2IPE30PL200x8w200x5', '2IPE30PL200x8w200x5', '2IPE30PL200x8','2IPE30PL200x8', '2IPE30w200x5', '2IPE30w200x5'], base_level=-1.2, pos=(0, 0), size="30")
    make_column_type([4, 3.2, 3.2, 3.2, 3.3, 5], ['2IPE24PL300x8w200x5', '2IPE24PL250x8w200x5', '2IPE24PL200x8','2IPE24PL200x8', '2IPE24w150x5', '2IPE24w150x5'], base_level=-1.2, pos=(2000, 0), size="24", pa_baz=True)
    # make_column_type([4, 3.2, 3.2, 3.2, 3.3, 5], ['2IPE24w200x5', '2IPE24PL250x8w200x5', '2IPE24PL200x8','2IPE24PL200x8', '2IPE24w150x5', '2IPE24w150x5'], base_level=-1.2, pos=(4000, 0), size="24", pa_baz=True)
    # make_column_type([4, 3.2, 3.2, 3.2, 3.3, 5], ['2IPE14', '2IPE14', '2IPE14', '2IPE14', '2IPE14', '2IPE14'], base_level=-1.2, pos=(6000, 0), size="14", pa_baz=True)
    # make_column_type([4, 3.2, 3.2, 3.2, 3.3, 5, 3, 3], ['3IPE18PL310x10w140x8', '3IPE18PL310x10', '3IPE18PL310x8', '3IPE18PL230x8', '3IPE18PL230x6', '3IPE18', '3IPE18', '3IPE18'], base_level=-1.2, pos=(8000, 0), size="18", pa_baz=True)
    # make_column_type([4, 3.2, 3.2, 3.2, 3.3, 5, 3, 3], ['2IPE18PL310x10w140x8', '2IPE18PL310x10', '2IPE18PL310x8', '2IPE18PL230x8', '2IPE18PL230x6', '2IPE18PL230x6', '2IPE18PL230x6', '2IPE18PL230x6w140x8'], base_level=-1.2, pos=(10000, 0), size="18", pa_baz=True)

    # make_column_type([4, 3.2, 3.2, 3.2, 3.3, 5, 3, 3], ['2IPE18PL310x10w140x8', '3IPE18PL310x10', '3IPE18', '2IPE18', '3IPE18PL310x10', '2IPE18', '2IPE18', '2IPE18'], base_level=-1.2, pos=(12000, 0), size="18", pa_baz=True)
    
    # make_column_type([4, 3.2, 3.2, 3.2, 3.3, 5, 3, 3], ['2IPE14', '3IPE14PL170x6', '3IPE14PL170x6', '3IPE14', '3IPE14', '3IPE14', '3IPE14', '3IPE14'], base_level=-1.2, pos=(14000, 0), size="14", pa_baz=True)
    # make_column_type([4, 3.2, 3.2, 3.2, 3.3, 5, 3, 3], ['2IPE14', '2IPE14', '2IPE14', '2IPE14', '2IPE14', '3IPE14', '3IPE14', '3IPE14'], base_level=-1.2, pos=(16000, 0), size="14", pa_baz=True)
    # make_column_type([4, 3.2, 3.2, 3.2, 3.3, 5, 3, 3], ['2IPE16', '3IPE16PL280x8', '3IPE16PL280x8', '3IPE16PL200x6', '3IPE16PL200x6', '3IPE16', '3IPE16'], base_level=-1.2, pos=(18000, 0), size="16", pa_baz=True)


