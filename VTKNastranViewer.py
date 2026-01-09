import vtk
import pyNastran
from pyNastran.bdf.bdf import BDF
from enum import Enum
class ParseMethod(Enum):
    Manual = 0
    pyNastran = 1
class vtkfilereader:
    def __init__(self, InputFileName:str, outputFileName:str, 
                      outputBDFName:str, logData:bool = False, writeData:bool = False, 
                      parse_method:ParseMethod = ParseMethod.pyNastran):
        if not InputFileName or not outputFileName:
            return
        self.InputFileName = InputFileName
        self.OutputFileName = outputFileName
        self.outputBDFName = outputBDFName
        self.logData = logData
        self.writeData = writeData
        self.nodeIDIndexMap = {}
        self.grid = vtk.vtkUnstructuredGrid()
        self.points = vtk.vtkPoints()
        if(parse_method == ParseMethod.Manual):
            self.n = 8      #parseSize
            self.grid_cnt = 0
            self.quad_cnt = 0
            self.tri_cnt = 0
            self.rbe_cnt = 0
            self.fo = None
            if(self.writeData):
                self.fo = open(outputBDFName, 'w')
            self.nodeIDs =[]
            self.readInputBDFFile()
            self.grid.SetPoints(self.points)
        elif(parse_method == ParseMethod.pyNastran):
            self.Model = BDF()
            self.Model.read_bdf(InputFileName)
            for (nodeID, node ) in self.Model.nodes.items():
                coord = self.Model.Coord(node.cp)
                gPos = coord._transform_node_to_global_array(node.xyz)
                gridIndex = self.points.InsertNextPoint(float(gPos[0]), float(gPos[1]), float(gPos[2]))
                vertex = vtk.vtkVertex()
                vertex.GetPointIds().SetId(0, gridIndex)
                self.grid.InsertNextCell(vertex.GetCellType(), vertex.GetPointIds())
                self.nodeIDIndexMap[nodeID] = gridIndex
            self.grid.SetPoints(self.points)
            element_type_to_vtk = {
                'CBAR': (vtk.vtkLine, 2),
                'CBUSH': (vtk.vtkLine, 2),
                'CTRIA3': (vtk.vtkTriangle, 3),
                'CTRIA6': (vtk.vtkQuadraticTriangle, 6),
                'CQUAD4': (vtk.vtkQuad, 4),
                'CQUAD8': (vtk.vtkQuadraticQuad, 8),
                'CTETRA': (vtk.vtkTetra, 4),
                'CTETRA10': (vtk.vtkQuadraticTetra, 10),
                'CPYRAMID': (vtk.vtkPyramid, 5),
            }
            for (eid, element) in self.Model.elements.items():
                vtk_cell_info = element_type_to_vtk.get(element.type)
                if vtk_cell_info is not None:
                    vtk_cell_cls, num_points = vtk_cell_info
                    self._insert_vtk_element(vtk_cell_cls, element.node_ids[:num_points])
                elif element.type == 'CPENTA6' or element.type == 'CPENTA15':
                    num_nodes = len(element.node_ids)
                    if num_nodes == 6:
                        vtk_cell_cls = vtk.vtkWedge
                    elif num_nodes == 15:
                        vtk_cell_cls = vtk.vtkQuadraticWedge
                    else:
                        continue
                    self._insert_vtk_element(vtk_cell_cls, element.node_ids)
                elif element.type == 'CHEXA' or element.type == 'CHEXA20':
                    num_nodes = len(element.node_ids)
                    if num_nodes == 8:
                        vtk_cell_cls = vtk.vtkHexahedron
                    elif num_nodes == 20:
                        vtk_cell_cls = vtk.vtkQuadraticHexahedron
                    else:
                        continue
                    self._insert_vtk_element(vtk_cell_cls, element.node_ids)
        #self.writeVTKFile()

    def readInputBDFFile(self):
        with open(self.InputFileName) as fp:
            line = fp.readline()
            while line:
                if line.find("GRID") != -1:
                    self.parseGridData(line)
                elif line.find("CTRIA3") != -1:
                    self.parseTriangleData(line)
                elif line.find("CQUAD4") != -1:
                    self.parseQuadData(line)
                elif line.find("RBE2 ") != -1:
                    self.parseRBE2Data(line)
                line = fp.readline()
       
    def parseGridData(self, line):
        #Coord = [] #to read and store coordinate systems initially to use
        if(self.logData):
            print("Grids {}: {}".format(self.grid_cnt, line.strip()))
        if(self.writeData and self.fo):
            self.fo.write(line)
        parsedLine = [line[i * self.n:i * self.n+self.n] for i,_ in enumerate(line[::self.n])]
        if(len(parsedLine) < 6):
            return
        rawCoords = parsedLine[3], parsedLine[4], parsedLine[5]
        # if parsedLine[2].isdigit() : 
        #    cp = int(float(parsedLine[2]))
        #    coord = Coord(cp)
        #    rawCoords = coord.transformToGlobal(rawCoords)
        pointIndex = self.points.InsertNextPoint(float(rawCoords[0]), float(rawCoords[1]), float(rawCoords[2]))
        vertex = vtk.vtkVertex()
        vertex.GetPointIds().SetId(0, pointIndex)    
        gridIndex = self.grid.InsertNextCell(vertex.GetCellType(), vertex.GetPointIds())
        self.nodeIDIndexMap[int(parsedLine[1])] = gridIndex
        self.grid_cnt += 1

    def parseRBE2Data(self, line):
        if(self.logData):
            print("RBE2s {}: {}".format(self.rbe_cnt, line.strip()))
        if(self.writeData and self.fo):
            self.fo.write(line)
        parsedLine = [line[i * self.n:i * self.n+self.n] for i,_ in enumerate(line[::self.n])]
        if(len(parsedLine) < 5):
            return
        elem = vtk.vtkLine()
        for i in range(0,2):
            gridIndex = self.nodeIDIndexMap[int(parsedLine[i + 3])]
            if(gridIndex < 0 or gridIndex >= self.grid_cnt):
                return
            elem.GetPointIds().SetId(i, gridIndex)
        self.grid.InsertNextCell(elem.GetCellType(), elem.GetPointIds())
        self.rbe_cnt += 1

    def parseTriangleData(self, line):
        if(self.logData):
            print("Trias {}: {}".format(self.tri_cnt, line.strip()))
        if(self.writeData and self.fo):
            self.fo.write(line)
        parsedLine = [line[i * self.n:i * self.n+self.n] for i,_ in enumerate(line[::self.n])]
        if(len(parsedLine) < 6):
            return
        elem = vtk.vtkTriangle()
        for i in range(0,3):
            gridIndex = self.nodeIDIndexMap[int(parsedLine[i + 3])]
            if(gridIndex < 0 or gridIndex >= self.grid_cnt):
                return
            elem.GetPointIds().SetId(i, gridIndex)
        self.grid.InsertNextCell(elem.GetCellType(), elem.GetPointIds())
        self.tri_cnt += 1

    def parseQuadData(self, line):
        if(self.logData):
            print("Quads {}: {}".format(self.quad_cnt, line.strip()))
        if(self.writeData and self.fo):
            self.fo.write(line)
        parsedLine = [line[i * self.n:i * self.n+self.n] for i,_ in enumerate(line[::self.n])]
        if(len(parsedLine) < 7):
            return
        elem = vtk.vtkQuad()
        for i in range(0,4):
            gridIndex = self.nodeIDIndexMap[int(parsedLine[i + 3])]
            if(gridIndex < 0 or gridIndex >= self.grid_cnt):
                return
            elem.GetPointIds().SetId(i, gridIndex)
        self.grid.InsertNextCell(elem.GetCellType(), elem.GetPointIds())
        self.quad_cnt += 1

    def writeVTKFile(self):
        if not self.OutputFileName:
            return
        writer = vtk.vtkUnstructuredGridWriter()
        writer.SetFileName(self.OutputFileName)
        writer.SetInputData(self.grid)
        writer.Write()

    def ShowVTK(self):
        GridMapper = vtk.vtkDataSetMapper()
        GridMapper.SetInputData(self.grid)
        Gridactor = vtk.vtkActor()
        Gridactor.SetMapper(GridMapper)
        Gridactor.GetProperty().SetColor(0.0, 0.0, 1.0)

        Geom = vtk.vtkGeometryFilter()
        Geom.SetInputData(self.grid)

        edges = vtk.vtkExtractEdges()
        edges.SetInputConnection(Geom.GetOutputPort())
        #edges.SetInputData(self.grid)
       # edges.Update()

        EdgeMapper = vtk.vtkPolyDataMapper()
        EdgeMapper.SetInputConnection(edges.GetOutputPort())
        Edgeactor = vtk.vtkActor()
        Edgeactor.SetMapper(EdgeMapper)
        Edgeactor.GetProperty().SetColor(1.0, 1.0, 1.0)

        renderer = vtk.vtkRenderer()
        renderer.AddActor(Gridactor)
        renderer.AddActor(Edgeactor)
        renderer.SetBackground(0.5, 0.5, 0.5) # Set background to white

        renderer_window = vtk.vtkRenderWindow()
        renderer_window.AddRenderer(renderer)
        
        interactor = vtk.vtkRenderWindowInteractor()
        interactor.SetRenderWindow(renderer_window)
        style = vtk.vtkInteractorStyleTrackballCamera()
        interactor.SetInteractorStyle(style)
        interactor.Initialize()
        interactor.Start()

    def _insert_vtk_element(self, vtk_cell_cls, node_ids):
        elem = vtk_cell_cls()
        num_points = len(node_ids)
        for i in range(num_points):
            try:
                elem.GetPointIds().SetId(i, self.nodeIDIndexMap[node_ids[i]])
            except KeyError:
                # Node ID not found; skip this element
                return False
        self.grid.InsertNextCell(elem.GetCellType(), elem.GetPointIds())
        return True

def main():
    #filein = r'E:\C\Model\FE\ex3_model.bdf'
    filein = r'E:\C\\WS\Python_Projects\TestCases\Input\FEModels\test1.bdf'
    localWrite = r'E:\C\Model\FE\Output\ex3_model2.bdf'
    fileout = r'E:\C\Model\FE\Output\nastran_file3.vtk'
    obj = vtkfilereader(filein, fileout, localWrite, False, False, ParseMethod.pyNastran)
    print("Conversion complete.")
    obj.ShowVTK()
    #obj.writeVTKFile()

if __name__ == "__main__" :
    main()