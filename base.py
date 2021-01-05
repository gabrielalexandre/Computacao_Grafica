import sys
import numpy as np
from OpenGL.GL import *
from OpenGL.GL import shaders
from OpenGL.GLUT import *
import glm
import threading
import time
import pywavefront
import pyrr
import os
from PIL import Image
from PIL import ImageOps

vao = None
vbo = None
shaderProgram = None    # none, phong, flat, smooth
shaderProgramAxis = None
shaderProgramLight = None
axis = False
lightFlag = False
wireFlag = False

CUBE = 0
CONE = 1
SPHERE = 2
TORUS = 3

WIDTH = 640
HEIGHT = 640

SIZEOF_FLOAT = 4
commands = []
objects = []
cena = {}
lights = {}

cam = glm.vec3(0, 0, 0)
lookat = glm.vec3(0, 0, -1)
up = glm.vec3(0, 1, 0)

ambient = 0.2
diffuse = 0.2
specular = 0.2


def readShaderFile(filename):
    with open(filename, 'r') as myfile:
        return myfile.read()


def transform(shader, m):
    # Passa matriz model para shader
    modelLoc = glGetUniformLocation(shader, "model")
    glUniformMatrix4fv(modelLoc, 1, GL_FALSE, np.array(m, dtype='f'))


def color(shader, m):
    # Define cor do objeto
    colorLoc = glGetUniformLocation(shader, "attrib_Color")
    glUniform3f(colorLoc, m[0], m[1], m[2])


def lightToShader():
    # Passa lista com luzes para shader
    tam = glGetUniformLocation(shaderProgram, "n")
    glUniform1f(tam, len(lights))

    # Passa cor da luz como branca para shader
    colorlightLoc = glGetUniformLocation(shaderProgram, "lightColor")
    glUniform3f(colorlightLoc, 1.0, 1.0, 1.0)

    posLoc = glGetUniformLocation(shaderProgram, "lightPos")
    # print(list(lights.values()))
    glUniform3fv(posLoc, len(lights), list(lights.values()))


def camToShader(cam):
    # Passa posicao da cam para shader
    cameraLoc = glGetUniformLocation(shaderProgram, "viewPos")
    glUniform3f(cameraLoc, cam[0], cam[1], cam[2])


def viewToShader(shader):
    # Passa matriz view para shader
    matrixView = glm.lookAt(cam, lookat, up)
    viewlLoc = glGetUniformLocation(shader, "view")
    glUniformMatrix4fv(viewlLoc, 1, GL_FALSE, np.array(matrixView, dtype='f'))


def projToShader(shader):
    # Passa matriz projection para shader
    matrixOrtho = pyrr.matrix44.create_orthogonal_projection(-2.0, 2.0, -2.0, 2.0, -2.0, 2.0, dtype='f')
    projLoc = glGetUniformLocation(shader, "proj")
    glUniformMatrix4fv(projLoc, 1, GL_FALSE, matrixOrtho)


def setShadeType(shader):
    # Seleciona shader atual
    global shaderProgram
    global ambient, diffuse, specular
    vertex_code = readShaderFile('shader330/' + shader + '.vp')
    fragment_code = readShaderFile('shader330/' + shader + '.fp')
    vertexShader = shaders.compileShader(vertex_code, GL_VERTEX_SHADER)
    fragmentShader = shaders.compileShader(fragment_code, GL_FRAGMENT_SHADER)
    shaderProgram = shaders.compileProgram(vertexShader, fragmentShader)
    glUseProgram(shaderProgram)
    initialConstantK()


def setConstantsK(typeReflection, v):
    # Define valor k para funcao reflection_on
    global ambient, diffuse, specular
    if typeReflection == "ambient":
        ambient = v
        ka = glGetUniformLocation(shaderProgram, "Ka")
        glUniform1f(ka, v)
    if typeReflection == "diffuse":
        diffuse = v
        kd = glGetUniformLocation(shaderProgram, "Kd")
        glUniform1f(kd, v)
    if typeReflection == "specular":
        specular = v
        ks = glGetUniformLocation(shaderProgram, "Ks")
        glUniform1f(ks, v)


def initialConstantK():
    # Define constantes k iniciais do programa
    ka = glGetUniformLocation(shaderProgram, "Ka")
    glUniform1f(ka, ambient)
    kd = glGetUniformLocation(shaderProgram, "Kd")
    glUniform1f(kd, diffuse)
    ks = glGetUniformLocation(shaderProgram, "Ks")
    glUniform1f(ks, specular)


def screenshot(filename):
    glutSwapBuffers()
    glPixelStorei(GL_PACK_ALIGNMENT, 1)
    data = glReadPixels(0, 0, WIDTH, HEIGHT, GL_RGBA, GL_UNSIGNED_BYTE)
    image = Image.frombytes("RGBA", (WIDTH, HEIGHT), data)
    image = ImageOps.flip(image)  # estava invertendo verticalmente por algum motivo, então colocamos essa linha
    if not os.path.exists('Screens'):
        os.makedirs('Screens')
    if os.path.isfile('Screens/'+filename+'.png'):
        os.remove('Screens/'+filename+'.png')
    image.save('Screens/'+filename+'.png', 'PNG')


def init():
    global shaderProgram
    global shaderProgramAxis
    global vao
    global vbo
    global objects
    global shaderProgramLight

    glClearColor(0, 0, 0, 0)

    vertex_code = readShaderFile('shader330/none.vp')
    fragment_code = readShaderFile('shader330/none.fp')

    vertex_axis = readShaderFile('shader330/eixo.vp')
    fragment_axis = readShaderFile('shader330/eixo.fp')

    vertex_light = readShaderFile('shader330/luz.vp')
    fragment_light = readShaderFile('shader330/luz.fp')

    # compile shaders and program
    vertexShader = shaders.compileShader(vertex_code, GL_VERTEX_SHADER)
    fragmentShader = shaders.compileShader(fragment_code, GL_FRAGMENT_SHADER)
    shaderProgram = shaders.compileProgram(vertexShader, fragmentShader)

    vertexShaderAxis = shaders.compileShader(vertex_axis, GL_VERTEX_SHADER)
    fragmentShaderAxis = shaders.compileShader(fragment_axis, GL_FRAGMENT_SHADER)
    shaderProgramAxis = shaders.compileProgram(vertexShaderAxis, fragmentShaderAxis)

    vertexlight = shaders.compileShader(vertex_light, GL_VERTEX_SHADER)
    fragmentlight = shaders.compileShader(fragment_light, GL_FRAGMENT_SHADER)
    shaderProgramLight = shaders.compileProgram(vertexlight, fragmentlight)

    # Need this line to use transformations in uniform
    glUseProgram(shaderProgram)

    # Create and bind the Vertex Array Object 

    vao = GLuint(0)
    glGenVertexArrays(1, vao)
    glBindVertexArray(vao)

    vbo = glGenBuffers(6)

    names = ['cube', 'cone', 'sphere', 'torus']

    eixo = np.array([9,0,0,1,0,0, -9,0,0,1,0,0, 0,9,0,0,1,0, 0,-9,0,0,1,0,
                    0,0,9,0,0,1, 0,0,-9,0,0,1,], dtype='f')

    glBindBuffer(GL_ARRAY_BUFFER, vbo[4])
    glBufferData(GL_ARRAY_BUFFER, eixo, GL_STATIC_DRAW)

    # Carregando todos vertices dos objs em uma lista objects
    for i in range(len(names)):
        scene = pywavefront.Wavefront('Objects/' + names[i] + '.obj', create_materials=True, collect_faces=True)
        objects.append(np.array(scene.mesh_list[0].materials[0].vertices, dtype='f'))
        # Criando vbos pra cada forma geometrica
        glBindBuffer(GL_ARRAY_BUFFER, vbo[i])
        glBufferData(GL_ARRAY_BUFFER, objects[i], GL_STATIC_DRAW)

    # matrixIdent = np.array(glm.mat4(), dtype='f')

    matrixOrtho = pyrr.matrix44.create_orthogonal_projection(-2.0, 2.0, -2.0, 2.0, -2.0, 2.0, dtype='f')

    # print(matrixOrtho)

    matrixView = glm.lookAt(cam, lookat, up)

    # Iniciando Ks com valor padrão 0.2
    initialConstantK()

    # estamos comentando a model, pois estamos considerando uma model para cada objeto, e é colocado inicialmente uma matriz 
    # identidade para cada objeto na cena, já que a matriz identidade representa escala 1 em todos os eixos, fazemos isso
    # na parte no comando add_shape, e todos os comandos estão localizados no display
    # modelLoc = glGetUniformLocation(shaderProgram, "model")
    # glUniformMatrix4fv(modelLoc, 1, GL_FALSE, np.array(matrixIdent, dtype='f'))
    viewlLoc = glGetUniformLocation(shaderProgram, "view")
    glUniformMatrix4fv(viewlLoc, 1, GL_FALSE, np.array(matrixView, dtype='f'))
    projLoc = glGetUniformLocation(shaderProgram, "proj")
    glUniformMatrix4fv(projLoc, 1, GL_FALSE, matrixOrtho)

    # Note that this is allowed, the call to glVertexAttribPointer registered VBO
    # as the currently bound vertex buffer object so afterwards we can safely unbind
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    # Unbind VAO (it's always a good thing to unbind any buffer/array to prevent strange bugs)
    glBindVertexArray(0)


def display():
    global shaderProgram
    global shaderProgramAxis
    global vao
    global commands
    global axis
    global objects
    global cena
    global cam
    global lookat
    global shaderProgramLight
    global lights
    global lightFlag
    global wireFlag

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    # load everything back
    glUseProgram(shaderProgram)
    glBindVertexArray(vao)

    # Colocando os objetos na cena, cada objeto tem um id e conjunto de vertices(opcional/retirado)
    # Cada comando contem uma lista de string, estando na posição 0 o comando, e nas subsequentes
    # os argumentos do comando

    if commands != []:
        command = commands.pop(0)
        if command[0] == 'add_shape':
            obj_name = command[2]
            # Cada objeto do add shape tem em sua estrutura na cena (id do poligono, nome do objeto que foi passado pelo usuario,
            # matriz identidade representando a escala de tamanho um em todos os eixos, e a cor branca que é RGB = 1,1,1)
            if command[1] == 'cube':
                cena[obj_name] = [CUBE, obj_name, glm.mat4(), (1.0, 1.0, 1.0)]
            if command[1] == 'cone':
                cena[obj_name] = [CONE, obj_name, glm.mat4(), (1.0, 1.0, 1.0)]
            if command[1] == 'sphere':
                cena[obj_name] = [SPHERE, obj_name, glm.mat4(), (1.0, 1.0, 1.0)]
            if command[1] == 'torus':
                cena[obj_name] = [TORUS, obj_name, glm.mat4(), (1.0, 1.0, 1.0)]
        elif command[0] == 'remove_shape':
            obj_name = command[1]
            del cena[obj_name]
        elif command[0] == 'scale':
            obj_name = command[1]
            m = glm.scale(cena[obj_name][2], glm.vec3((float(command[2]), float(command[3]), float(command[4]))))
            # print(m)
            cena[obj_name][2] = m
        elif command[0] == 'rotate':
            obj_name = command[1]
            m = glm.rotate(cena[obj_name][2], float(command[2]),
                           glm.vec3(float(command[3]), float(command[4]), float(command[5])))
            # print(m)
            cena[obj_name][2] = m
        elif command[0] == 'translate':
            obj_name = command[1]
            m = glm.translate(cena[obj_name][2], glm.vec3((float(command[2]), float(command[3]), float(command[4]))))
            # print(m)
            cena[obj_name][2] = m
        elif command[0] == 'shear':
            obj_name = command[1]
            shearyx = float(command[2])
            shearzx = float(command[3])
            shearxy = float(command[4])
            shearzy = float(command[5])
            shearxz = float(command[6])
            shearyz = float(command[7])

            shear_matrix = np.array([[1.0, shearxy, shearxz, 0.0],
                            [shearyx, 1.0, shearyz, 0.0],
                            [shearzx, shearzy, 1.0, 0.0],
                            [0.0, 0.0, 0.0, 1.0]], dtype='f').T

            shear_matrix = glm.mat4(shear_matrix.tolist())

            # print(shear_matrix)
            m = cena[obj_name][2] * shear_matrix
            # print(m)
            cena[obj_name][2] = glm.mat4(m)
        elif command[0] == 'color':
            obj_name = command[1]
            cena[obj_name][3] = (float(command[2]), float(command[3]), float(command[4]))
        elif command[0] == 'cam':
            cam = glm.vec3(float(command[1]), float(command[2]), float(command[3]))
        elif command[0] == 'lookat':
            lookat = glm.vec3(float(command[1]), float(command[2]), float(command[3]))
        elif command[0] == 'axis_on':
            axis = True
        elif command[0] == 'axis_off':
            axis = False
        elif command[0] == 'shading':
            tipo = command[1]
            setShadeType(tipo)
        elif command[0] == 'add_light':
            obj_name = command[1]
            lightPos = [float(command[2]), float(command[3]), float(command[4])]
            lights[obj_name] = lightPos
        elif command[0] == 'remove_light':
            obj_name = command[1]
            del lights[obj_name]
        elif command[0] == 'reflection_on':
            typeReflection = command[1]
            setConstantsK(typeReflection, float(command[2]))
        elif command[0] == 'reflection_off':
            typeReflection = command[1]
            setConstantsK(typeReflection, 0.0)
        elif command[0] == 'lights_on':
            lightFlag = True
        elif command[0] == 'lights_off':
            lightFlag = False
        elif command[0] == 'wire_on':
            wireFlag = True
        elif command[0] == 'wire_off':
            wireFlag = False
        elif command[0] == 'save':
            filename = command[1]
            screenshot(filename)
        elif command[0] == 'quit':
            glutLeaveMainLoop()
        else:
            print("NOT IMPLEMENTED")
        command = []

    # Passa vetor de luzes para shader
    lightToShader()

    # Passa cam para shader
    camToShader(cam)

    # Carregando dados do vbo e desenhando objetos da cena
    for obj in cena:
        # Seleciona shader atual
        glUseProgram(shaderProgram)
        glEnableVertexAttribArray(0)
        glEnableVertexAttribArray(1)

        # Passa matriz de transformacao do obj para shader
        transform(shaderProgram, cena[obj][2])

        # Define cor do objeto
        color(shaderProgram, cena[obj][3])

        # Passa matriz view para shader
        viewToShader(shaderProgram)

        # Passa matriz projection para shader
        projToShader(shaderProgram)

        if wireFlag:
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        else:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        if cena[obj][0] == CUBE:
            glBindBuffer(GL_ARRAY_BUFFER, vbo[0])
            glVertexAttribPointer(0, 3, GL_FLOAT, False, SIZEOF_FLOAT * 8, ctypes.c_void_p(4 * 5)) # 5, 6, 7 -> vertices
            glVertexAttribPointer(1, 3, GL_FLOAT, False, SIZEOF_FLOAT * 8, ctypes.c_void_p(4 * 2)) # 2, 3, 4 -> normais
            glEnable(GL_DEPTH_TEST)
            glDrawArrays(GL_TRIANGLES, 0, int(108/3))
        elif cena[obj][0] == CONE:
            glBindBuffer(GL_ARRAY_BUFFER, vbo[1])
            glVertexAttribPointer(0, 3, GL_FLOAT, False, SIZEOF_FLOAT * 8, ctypes.c_void_p(4 * 5)) # 5, 6, 7 -> vertices
            glVertexAttribPointer(1, 3, GL_FLOAT, False, SIZEOF_FLOAT * 8, ctypes.c_void_p(4 * 2)) # 2, 3, 4 -> normais
            glEnable(GL_DEPTH_TEST)
            glDrawArrays(GL_TRIANGLES, 0, int(558/3))
        elif cena[obj][0] == SPHERE:
            glBindBuffer(GL_ARRAY_BUFFER, vbo[2])
            glVertexAttribPointer(0, 3, GL_FLOAT, False, SIZEOF_FLOAT * 8, ctypes.c_void_p(4 * 5)) # 5, 6, 7 -> vertices
            glVertexAttribPointer(1, 3, GL_FLOAT, False, SIZEOF_FLOAT * 8, ctypes.c_void_p(4 * 2)) # 2, 3, 4 -> normais
            glEnable(GL_DEPTH_TEST)
            glDrawArrays(GL_TRIANGLES, 0, int(46080/3))
        elif cena[obj][0] == TORUS:
            glBindBuffer(GL_ARRAY_BUFFER, vbo[3])
            glVertexAttribPointer(0, 3, GL_FLOAT, False, SIZEOF_FLOAT * 8, ctypes.c_void_p(4 * 5)) # 5, 6, 7 -> vertices
            glVertexAttribPointer(1, 3, GL_FLOAT, False, SIZEOF_FLOAT * 8, ctypes.c_void_p(4 * 2)) # 2, 3, 4 -> normais
            glEnable(GL_DEPTH_TEST)
            glDrawArrays(GL_TRIANGLES, 0, int(10368/3))

    # Verifica se comand lights_on esta ativo
    if lightFlag:
        for light in lights:
            glUseProgram(shaderProgramLight)
            glEnableVertexAttribArray(0)

            # Passa matriz view para shader
            viewToShader(shaderProgramLight)

            # Passa matriz projection para shader
            projToShader(shaderProgramLight)

            # Acessa posicao da luz no vetor lights e manda para vbo
            pos = lights[light]
            glBindBuffer(GL_ARRAY_BUFFER, vbo[5])
            glBufferData(GL_ARRAY_BUFFER, np.array(pos, dtype='f'), GL_STATIC_DRAW)

            # Define cor da luz como Yellow
            color(shaderProgramLight, (1.0, 1.0, 0.0))

            # Desenha luzes
            glVertexAttribPointer(0, 3, GL_FLOAT, False, SIZEOF_FLOAT * 3, None)
            glPointSize(8)
            glDrawArrays(GL_POINTS, 0, 1)
            glDisableVertexAttribArray(0)


    # desativar aqui
    glUseProgram(shaderProgram)
    glDisableVertexAttribArray(0)
    glDisableVertexAttribArray(1)

    if axis:
        glUseProgram(shaderProgramAxis)
        glEnableVertexAttribArray(0)
        glEnableVertexAttribArray(1)

        # Passa matriz view para shader
        viewToShader(shaderProgramAxis)

        # Passa matriz projection para shader
        projToShader(shaderProgramAxis)

        glBindBuffer(GL_ARRAY_BUFFER, vbo[4])
        glVertexAttribPointer(0, 3, GL_FLOAT, False, SIZEOF_FLOAT * 6, ctypes.c_void_p(4 * 0)) # X, Y, Z
        glVertexAttribPointer(1, 3, GL_FLOAT, False, SIZEOF_FLOAT * 6, ctypes.c_void_p(4 * 3)) # R, G, B
        glDrawArrays(GL_LINES, 0, int(6))

        glDisableVertexAttribArray(0)
        glDisableVertexAttribArray(1)

    # clean things up
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)
    glUseProgram(0)

    glutSwapBuffers()  # necessario para windows!


def reshape(width, height):
    glViewport(0, 0, width, height)


def entry():
    global commands
    while True:
        # Para que os comandos passados sejam executados rapidamente inserir um valor entre 0.14 a 0.5 abaixo
        # time sleep
        time.sleep(0.14)
        entrada = input("Digite a entrada: ")
        # Commands eh uma lista de listas com as palavras ja separadas (pode ser inserido vários comandos de uma vez)
        entradaLinhas = entrada.splitlines()
        for i in entradaLinhas:
            commands.append(i.split())
            
        print(commands)
        # glutPostRedisplay()


if __name__ == '__main__':
    glutInit()
    glutInitContextVersion(3, 0)
    glutInitContextProfile(GLUT_CORE_PROFILE)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)

    glutInitWindowSize(WIDTH, HEIGHT)
    glutCreateWindow(b'Visualizador Geometrico')

    glutReshapeFunc(reshape)
    glutDisplayFunc(display)
    glutIdleFunc(display)

    # Ativa thread para funcao entry ficar escaneando entradas de forma paralela
    my_thread = threading.Thread(target=entry)
    my_thread.daemon = True
    my_thread.start()

    init()

    glutMainLoop()
