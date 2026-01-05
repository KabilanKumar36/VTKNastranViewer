import vtk
import pyNastran.bdf.bdf as BDF
class vtkfilereader:
    def __init__(self, InputFileName:str, outputFileName:str, 
                      outputBDFName:str, logData:bool = False, writeData:bool = False):
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
        Coord = []
        if(self.logData):
            print("Grids {}: {}".format(self.grid_cnt, line.strip()))
        if(self.writeData and self.fo):
            self.fo.write(line)
        parsedLine = [line[i * self.n:i * self.n+self.n] for i,_ in enumerate(line[::self.n])]
        #if parsedLine[2].isdigit() : 
        #    cp = int(float(parsedLine[2]))
        #    coord = Coord(cp)
        #    pos = coord.transformToGlobal(node.xyz) #position
        #    gpos = pos[0] #gridposition
        if(len(parsedLine) < 6):
            return
        Coord.append(float(parsedLine[3])) #x
        Coord.append(float(parsedLine[4])) #y
        Coord.append(float(parsedLine[5])) #z
        pointIndex = self.points.InsertNextPoint(*Coord)
        Coord.clear()
        vertex = vtk.vtkVertex()
        vertex.GetPointIds().SetId(0, pointIndex)    
        gridIndex = self.grid.InsertNextCell(vertex.GetCellType(), vertex.GetPointIds())
        self.nodeIDIndexMap[int(parsedLine[1])] = gridIndex
        self.grid_cnt += 1

    def parseRBE2Data(self, line):
        if(self.logData):
            print("RBE2s {}: {}".format(rbe_cnt, line.strip()))
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

def main():
    filein = r'E:\C\Model\FE\ex3_model.bdf'
    localWrite = r'E:\C\Model\FE\Output\ex3_model2.bdf'
    fileout = r'E:\C\Model\FE\Output\nastran_file3.vtk'
    obj = vtkfilereader(filein, fileout, localWrite, False, False)
    print("Conversion complete.")
    obj.ShowVTK()
    #obj.writeVTKFile()

if __name__ == "__main__" :
    main()