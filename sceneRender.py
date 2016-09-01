# -*- coding: utf-8 -*-
#import inspect
#import logging

import OpenGL
OpenGL.ERROR_CHECKING = False
OpenGL.ERROR_LOGGING = False

from OpenGL.GL import *
from OpenGL.GLU import *

import math

import numpy
import time

#from PyQt4.QtCore import QTimer
#from PyQt4.QtGui import QColor, QCursor
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtOpenGL import *
from PyQt4 import QtCore

from PIL.Image import *

import controller
#from camera import TargetedCamera
from glButton import GlButton

#Mesure
def timing(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        print('%s function took %0.3f ms' % (f.func_name, (time2-time1)*1000.0))
        return ret
    return wrap


class GLWidget(QGLWidget):
    def __init__(self, parent=None):
        #QGLWidget.__init__(self, parent)
        if hasattr(QGLFormat, 'setVersion'):
            f = QGLFormat()
            f.setVersion(2, 1)
            f.setDoubleBuffer(True)
            f.setSampleBuffers(True)
            f.setSamples(4)
            f.setSwapInterval(1)
            f.setProfile(QGLFormat.CoreProfile)
            c = QGLContext(f, None)
            QGLWidget.__init__(self, c, parent)
        else:
            QGLWidget.__init__(self, parent)

        self.setMouseTracking(True)

        self.parent = parent
        self.controller = self.parent.controller
        self.init_parametres()

        self.last_time = time.time()
        self.delta_t = 0.016
        self.last_fps = 100.
        self.fps_count = 0
        self.fps_time = 0.


        #properties definition
        self.xRot = 0
        self.yRot = 0
        self.zRot = 0
        self.zoom = 0
        self.camera_position = numpy.array([0., 4. ,0.])

        self.oldPos3d = [.0, .0, .0]

        self.lightAmbient = [.0, .0, .0, .0]
        self.lightDiffuse = [.0, .0, .0, .0]
        self.lightPossition = [.0, .0, .0, .0]

        self.materialSpecular = [.0,.0,.0,.0]
        self.materialShiness = [.0]

        #DEBUG
        self.rayStart = numpy.array([0., 0. ,0.])
        self.rayDir = numpy.array([0., 0. ,0.])
        self.rayUp = numpy.array([0., 0. ,0.])
        self.rayRight = numpy.array([0., 0. ,0.])
        #DEBUG

        #screen properties
        self.w = 0
        self.h = 0

        self.init_parametres()

        self.sceneFrameBuffer = []
        self.image_background = []
        self.image_hotbed = []

        #tools
        self.selectTool = None
        self.moveTool = None
        self.rotateTool = None
        self.scaleTool = None
        self.placeOnFaceTool = None
        self.tool_background = None
        self.do_button = None
        self.undo_button = None


    def init_parametres(self):
        #TODO:Add camera instance initialization
        #properties initialization
        self.xRot = 424
        self.yRot = 0
        self.zRot = 5576
        self.zoom = -39
        self.last_fps = 100.
        self.fps_count = 0
        self.fps_time = 0.

        self.oldPos3d = [.0, .0, .0]

        self.lightAmbient = [.95, .95, .95, 1.0]
        self.lightDiffuse = [.5, .5, .5, 1.0]
        self.lightPossition = [29.0, -48.0, 37.0, 1.0]

        self.materialSpecular = [.1, .1, .1, .1]
        self.materialShiness = [0.01]

        #screen properties
        self.w = 0
        self.h = 0

        self.sceneFrameBuffer = []
        self.tools = []


    '''
    def keyPressEvent(self, e):
        print(str(e))
        if e.key() == QtCore.Qt.Key_Escape:
            self.close()
    '''

    def keyPressEvent(self, event):
        self.controller.key_press_event(event)


    def mousePressEvent(self, event):
        self.controller.mouse_press_event(event)


    def mouseDoubleClickEvent(self, event):
        self.controller.mouse_double_click(event)

    def mouseReleaseEvent(self, event):
        self.controller.mouse_release_event(event)

    def mouseMoveEvent(self, event):
        self.controller.mouse_move_event(event)

    def wheelEvent(self, event):
        self.controller.wheel_event(event)


    def update_scene(self, reset=False):

        #if reset:
        #    self.init_parametres()

        #self.updateGL()
        self.update()


    #TODO:All this function will be changed to control camera instance
    def set_zoom(self, diff):
        #self.camera.add_zoom(diff)
        if (self.zoom + diff >= -60.0) and (self.zoom + diff <= -10.0):
            self.zoom += diff


    def get_zoom(self):
        #return self.camera.get_zoom()
        return self.zoom

    def get_x_rotation(self):
        return self.xRot

    def get_y_rotation(self):
        return self.yRot

    def get_z_rotation(self):
        return self.zRot

    def minimumSizeHint(self):
        return QtCore.QSize(50, 50)

    def sizeHint(self):
        return QtCore.QSize(600, 480)

    def set_x_rotation(self, angle):
        angle = self.normalize_angle_x(angle)
        if angle != self.xRot:
            self.xRot = angle

    def set_y_rotation(self, angle):
        angle = self.normalize_angle(angle)
        if angle != self.yRot:
            self.yRot = angle

    def set_z_rotation(self, angle):
        angle = self.normalize_angle(angle)
        if angle != self.zRot:
            self.zRot = angle

    def texture_from_png(self, filename):
        mode_to_bpp = {'1':1, 'L':8, 'P':8, 'RGB':24, 'RGBA':32, 'CMYK':32, 'YCbCr':24, 'I':32, 'F':32}

        img = open(filename)
        img = img.transpose(FLIP_TOP_BOTTOM)
        bpp = mode_to_bpp[img.mode]
        if bpp == 32:
            type = GL_RGBA
        else:
            type = GL_RGB
        img_data = numpy.array(list(img.getdata()), numpy.uint8)

        texture = glGenTextures(1)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glBindTexture(GL_TEXTURE_2D, texture)

        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, type, img.size[0], img.size[1], 0, type, GL_UNSIGNED_BYTE, img_data)
        return texture

    def initializeGL(self):
        #load textures
        self.image_background = self.texture_from_png("data/img/background.png")

        #tools
        #self.selectTool = GlButton(self.texture_from_png("data/img/select_ns.png"), [3.,3.], [95.5, 18])
        #self.moveTool = GlButton(self.texture_from_png("data/img/move_ns.png"), [3.,3.], [95.5, 12.])
        self.rotateTool = GlButton(self.texture_from_png("data/img/rotate_ns.png"), [45., 45.], [-50., 100.])
        self.scaleTool = GlButton(self.texture_from_png("data/img/scale_ns.png"), [45., 45.], [-50., 50])
        self.placeOnFaceTool = GlButton(self.texture_from_png("data/img/placeonface.png"), [45., 45.], [-50., 0])
        #back, forward buttons
        self.undo_button = GlButton(self.texture_from_png("data/img/undo_s.png"), [45., 45.], [0, -50], True)
        self.do_button = GlButton(self.texture_from_png("data/img/do_s.png"), [45., 45.], [45, -50], True)


        #self.selectTool.set_callback(self.parent.controller.select_button_pressed)
        #self.moveTool.set_callback(self.parent.controller.move_button_pressed)
        self.rotateTool.set_callback(self.controller.rotate_button_pressed)
        self.scaleTool.set_callback(self.controller.scale_button_pressed)
        self.placeOnFaceTool.set_callback(self.controller.place_on_face_button_pressed)
        self.undo_button.set_callback(self.controller.undo_button_pressed)
        self.do_button.set_callback(self.controller.do_button_pressed)


        self.tool_background = self.texture_from_png("data/img/tool_background.png")

        self.tools = [self.rotateTool, self.scaleTool, self.placeOnFaceTool, self.undo_button, self.do_button]
        #self.tools = []

        self.bed = {}
        for i in self.parent.controller.printers:
            self.bed[i['name']] = self.makePrintingBed(i['texture'], i['printing_space'])


        glClearDepth(1.0)
        glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_FALSE)
        glShadeModel(GL_FLAT)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)

        #NICE
        glCullFace(GL_FRONT)

        glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)

        #new light settings
        glLightfv(GL_LIGHT0, GL_POSITION, _gl_vector(50, 50, 100, 0))
        glLightfv(GL_LIGHT0, GL_SPECULAR, _gl_vector(.5, .5, 1, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, _gl_vector(1, 1, 1, 1))
        glLightfv(GL_LIGHT1, GL_POSITION, _gl_vector(100, 0, 50, 0))
        glLightfv(GL_LIGHT1, GL_DIFFUSE, _gl_vector(.5, .5, .5, 1))
        glLightfv(GL_LIGHT1, GL_SPECULAR, _gl_vector(1, 1, 1, 1))
        #new light settings

        #material
        glMaterialfv(GL_FRONT, GL_SPECULAR, self.materialSpecular)
        glMaterialfv(GL_FRONT, GL_SHININESS, self.materialShiness)


        glColorMaterial(GL_FRONT, GL_AMBIENT_AND_DIFFUSE)
        glEnable(GL_COLOR_MATERIAL)
        glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)

        glEnable( GL_LIGHT0 )
        glEnable( GL_LIGHT1 )


    #@timing

    def picking_render(self):
        glClearColor(0., 0., 0., 0.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)


        glLoadIdentity()
        glTranslatef(0.0, 0.0, self.zoom)
        glRotated(-90.0, 1.0, 0.0, 0.0)
        glRotated(self.xRot / 16.0, 1.0, 0.0, 0.0)
        glRotated(self.zRot / 16.0, 0.0, 0.0, 1.0)

        glTranslatef(-self.camera_position[0], -self.camera_position[1], -self.camera_position[2])

        glDisable(GL_LIGHTING)
        glDisable(GL_BLEND)


        for model in self.parent.controller.scene.models:
            if not model.isVisible:
                break
            model.render(picking=True, blending=True)
            if model.selected:
                self.draw_tools_helper(model, self.controller.settings, True)

        self.draw_tools(picking=True)


    def get_id_under_cursor(self, x, y):
        print("color_picking")
        self.picking_render()
        viewport = glGetIntegerv(GL_VIEWPORT)
        color = glReadPixels(x, viewport[3] - y, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE)
        return ord(color[0])+(256*ord(color[1]))+(256*256*ord(color[2]))


    def paintGL(self, selection = 1):
        t0 = time.time()
        heat_bed = self.bed[self.controller.settings['printer']]
        printer = None
        for p in self.controller.printers:
            if p['name'] == self.controller.settings['printer']:
                printer = p['printing_space']

        model_view = self.controller.render_status in ['model_view']

        #glDepthMask(GL_TRUE)
        glEnable( GL_LIGHTING )
        #glClearColor(0.0, 0.47, 0.62, 1.0)
        #glClearColor((176./255.),(236/255.) ,(255./255.), 1.0)
        glClearColor(0., 0., 0., 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self.draw_background_texture()
        glLoadIdentity()

        glTranslatef(0.0, 0.0, self.zoom)
        glRotated(-90.0, 1.0, 0.0, 0.0)
        glRotated(self.xRot / 16.0, 1.0, 0.0, 0.0)
        glRotated(self.zRot / 16.0, 0.0, 0.0, 1.0)

        glTranslatef(-self.camera_position[0], -self.camera_position[1], -self.camera_position[2])

        glLightfv(GL_LIGHT0, GL_POSITION, [0., 50., 100., 0.])
        glLightfv(GL_LIGHT1, GL_POSITION, [50., 10., 50., 0.])

        glCallList(heat_bed)

        glEnable(GL_DEPTH_TEST)

        #self.draw_debug()

        glEnable ( GL_LIGHTING )
        for model in self.parent.controller.scene.models:
            if not model.isVisible:
                break
            model.render(picking=False, blending=not model_view)
        glDisable( GL_LIGHTING )

        if not model_view:
            self.draw_layer(self.controller.gcode_layer, printer)



        for model in self.parent.controller.scene.models:
            if not model.isVisible:
                break
            if model.selected and model_view:
                self.draw_tools_helper(model, self.parent.controller.settings)


        if self.controller.render_status in ['model_view']:

            if not len(self.parent.controller.scene.analyze_result_data_tmp) == 0:
                glColor3f(1., .0, .0)
                glEnableClientState(GL_VERTEX_ARRAY)
                glEnableClientState(GL_NORMAL_ARRAY)
                glVertexPointerf(self.controller.scene.analyze_result_data_tmp)
                glDrawArrays(GL_TRIANGLES, 0, len(self.controller.scene.analyze_result_data_tmp)*3)
                glDisableClientState(GL_VERTEX_ARRAY)
                glDisableClientState(GL_NORMAL_ARRAY)

            self.draw_tools()

        #self.picking_render()
        glFlush()

        t1 = time.time()


        if self.fps_count==100:
            self.last_fps = 1./(self.fps_time/self.fps_count)
            self.fps_count = 0
            self.fps_time = 0.
            self.parent.controller.show_message_on_status_bar("FPS: %s" % str(self.last_fps))
        else:
            self.fps_count+=1
            self.fps_time+=t1-t0

    def draw_layer(self, layer, printing_space):
        #print("Drawing gcode layer " + str(self.controller.gcode_layer))
        layer_data = self.controller.gcode.data[self.controller.gcode_layer]
        #print("Data: " + str(layer_data))
        glPushMatrix()
        #TODO: Better solution
        glTranslatef(printing_space[0]*-0.5, printing_space[1]*-0.5, 0.0)

        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        glColor3f(1.0, 0.0, 0.0)
        glLineWidth(1.0)

        glBegin(GL_LINE_STRIP)
        for p in layer_data:
            glVertex3f(p[0]*.1, p[1]*.1, float(self.controller.gcode_layer)*.1)
        glEnd()

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glPopMatrix()
        #print(str(self.controller.gcode.data[self.controller.gcode_layer]))




    def draw_tools_helper(self, model, settings, picking=False):
        if picking:
            rotateColors = [model.rotateColorXId, model.rotateColorYId, model.rotateColorZId]
        else:
            rotateColors = [[180,180,180],[180,180,180],[180,180,180]]

        if settings['toolButtons']['rotateButton']:
            self.draw_rotation_circles(model, rotateColors, [i+o for i,o in zip(model.boundingSphereCenter, model.pos)], model.boundingSphereSize, picking)

    def draw_rotation_circles(self, model, colors, position, radius, picking=False):
        if not picking:
                colors[2] = [255, 255, 0]

        segments = 64
        glPushMatrix()
        glTranslatef(position[0], position[1], 0.0)
        glDisable( GL_LIGHTING )
        glDisable(GL_DEPTH_TEST)
        glLineWidth(4.0)
        glColor3ubv(colors[0])
        glBegin(GL_LINE_LOOP)
        glColor3ubv(colors[2])
        glBegin(GL_LINE_LOOP)
        for i in xrange(0, 360, 360/segments):
            glVertex3f(math.cos(math.radians(i)) * radius, math.sin(math.radians(i)) * radius, 0.0)
        glEnd()
        glEnable(GL_DEPTH_TEST)
        glEnable( GL_LIGHTING )
        glPopMatrix()


    def draw_debug(self):
        glPushMatrix()
        glDisable(GL_LIGHTING)
        glColor3f(1.,.0,.0)
        glBegin(GL_LINES)
        glVertex3f(self.rayStart[0], self.rayStart[1], self.rayStart[2])
        glVertex3f(self.rayDir[0]+self.rayStart[0], self.rayDir[1]+self.rayStart[1], self.rayDir[2]+self.rayStart[2])
        glColor3f(0.,1.0,.0)
        glVertex3f(self.rayStart[0], self.rayStart[1], self.rayStart[2])
        glVertex3f(self.rayUp[0], self.rayUp[1], self.rayUp[2])
        glColor3f(0.,.0,.1)
        glVertex3f(self.rayStart[0], self.rayStart[1], self.rayStart[2])
        glVertex3f(self.rayRight[0], self.rayRight[1], self.rayRight[2])
        glEnd()
        glEnable(GL_LIGHTING)
        glPopMatrix()


    def resizeGL(self, width, height):
        self.w = width
        self.h = height
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45., float(width*1./height*1.), 1., 75.)
        glMatrixMode(GL_MODELVIEW)

    def get_cursor_position(self, event):
        matModelView = glGetDoublev(GL_MODELVIEW_MATRIX )
        matProjection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv( GL_VIEWPORT )

        winX = event.x() * 1.0
        winY = viewport[3] - (event.y() *1.0)

        rayStart = gluUnProject(winX, winY, -1.0, matModelView, matProjection, viewport)
        rayEnd = gluUnProject(winX, winY, 1.0, matModelView, matProjection, viewport)

        return (rayStart, rayEnd)

    def get_camera_direction(self, event):
        matModelView = glGetDoublev(GL_MODELVIEW_MATRIX )
        matProjection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv( GL_VIEWPORT )

        winX = (viewport[2]*.5)
        winY = (viewport[3]*.5)

        rayStart = numpy.array(gluUnProject(winX, winY, 0.0, matModelView, matProjection, viewport))
        rayEnd = numpy.array(gluUnProject(winX, winY, 1.0, matModelView, matProjection, viewport))

        rayUp = numpy.array(gluUnProject(winX, winY + 10., 0.0, matModelView, matProjection, viewport))
        rayUp = rayUp - rayStart
        rayUp /= numpy.linalg.norm(rayUp)
        self.rayUp = rayUp

        rayRight = numpy.array(gluUnProject(winX + 10., winY, 0.0, matModelView, matProjection, viewport))
        rayRight = rayRight - rayStart
        rayRight /= numpy.linalg.norm(rayRight)
        self.rayRight = rayRight
        '''
        self.rayStart = rayStart
        self.rayDir = (rayEnd - rayStart)/(numpy.linalg.norm(rayEnd - rayStart))
        self.rayUp = rayUp
        self.rayRight = rayRight
        '''

        rayDir = (rayEnd - rayStart)/(numpy.linalg.norm(rayEnd - rayStart))

        return rayStart, rayDir, rayUp, rayRight



    def makePrintingBed(self, bed_texture, printing_space):
        image_hotbed = self.texture_from_png(bed_texture)

        genList = glGenLists(1)
        glNewList(genList, GL_COMPILE)

        glLineWidth(2)

        glEnable(GL_TEXTURE_2D)
        glDisable(GL_BLEND)
        glBindTexture(GL_TEXTURE_2D, image_hotbed)

        glColor3f(1,1,1)
        glBegin(GL_QUADS)
        glNormal3f(.0,.0,1.)
        glTexCoord2f(0, printing_space[1]*.5)
        glVertex3d(printing_space[0]*-0.5, printing_space[1]*0.5, -0.001)

        glTexCoord2f(0, 0)
        glVertex3d(printing_space[0]*-0.5, printing_space[1]*-0.5, -0.001)

        glTexCoord2f(printing_space[0]*.5, 0)
        glVertex3d(printing_space[0]*0.5, printing_space[1]*-0.5, -0.001)

        glTexCoord2f(printing_space[0]*.5, printing_space[1]*.5)
        glVertex3d(printing_space[0]*0.5, printing_space[1]*0.5, -0.001)
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBegin(GL_LINES)
        glColor3f(1,1,1)
        glVertex3d(printing_space[0]*-0.5, printing_space[1]*0.5, 0)
        glVertex3d(printing_space[0]*-0.5, printing_space[1]*0.5, printing_space[2])

        glVertex3d(printing_space[0]*0.5, printing_space[1]*0.5, 0)
        glVertex3d(printing_space[0]*0.5, printing_space[1]*0.5, printing_space[2])

        glVertex3d(printing_space[0]*0.5, printing_space[1]*-0.5, 0)
        glVertex3d(printing_space[0]*0.5, printing_space[1]*-0.5, printing_space[2])

        glVertex3d(printing_space[0]*-0.5, printing_space[1]*-0.5, 0)
        glVertex3d(printing_space[0]*-0.5, printing_space[1]*-0.5, printing_space[2])
        glEnd()

        glBegin(GL_LINE_LOOP)
        glVertex3d(printing_space[0]*-0.5, printing_space[1]*0.5, printing_space[2])
        glVertex3d(printing_space[0]*0.5, printing_space[1]*0.5, printing_space[2])
        glVertex3d(printing_space[0]*0.5, printing_space[1]*-0.5, printing_space[2])
        glVertex3d(printing_space[0]*-0.5, printing_space[1]*-0.5, printing_space[2])
        glEnd()

        #Axis
        glLineWidth(5)
        glDisable(GL_DEPTH_TEST)
        glBegin(GL_LINES)
        glColor3f(1, 0, 0)
        glVertex3d(printing_space[0]*-0.5, printing_space[1]*-0.5, 0)
        glVertex3d((printing_space[0]*-0.5)-1, printing_space[1]*-0.5, 0)

        glColor3f(0, 1, 0)
        glVertex3d(printing_space[0]*-0.5, printing_space[1]*-0.5, 0)
        glVertex3d(printing_space[0]*-0.5, (printing_space[1]*-0.5)-1, 0)

        glColor3f(0, 0, 1)
        glVertex3d(printing_space[0]*-0.5, printing_space[1]*-0.5, 0)
        glVertex3d(printing_space[0]*-0.5, printing_space[1]*-0.5, 1)
        glEnd()
        glEndList()
        glEnable(GL_DEPTH_TEST)

        return genList

    def make_axis(self):
        genList = glGenLists(1)
        glNewList(genList, GL_COMPILE)

        glLineWidth(5)

        glBegin(GL_LINES)

        glColor3f(1, 0, 0)
        glVertex3d(-10, -10, 0)
        glVertex3d(-9, -10, 0)

        glColor3f(0, 1, 0)
        glVertex3d(-10, -10, 0)
        glVertex3d(-10, -9, 0)

        glColor3f(0, 0, 1)
        glVertex3d(-10, -10, 0)
        glVertex3d(-10, -10, 1)

        glEnd()
        glEndList()

        return genList

    def draw_background_texture(self):
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        viewport = glGetIntegerv( GL_VIEWPORT )
        glOrtho(0.0, viewport[2], 0.0, viewport[3], 0.0, 1.0)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()

        glLoadIdentity()
        glDisable(GL_LIGHTING)
        glDisable(GL_BLEND)
        glDisable(GL_DEPTH_TEST)

        glColor3f(1,1,1)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.image_background)

        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex3f(0, 0, 0)

        glTexCoord2f(0, 1)
        glVertex3f(0, viewport[3], 0)

        glTexCoord2f(1, 1)
        glVertex3f(viewport[2], viewport[3], 0)

        glTexCoord2f(1, 0)
        glVertex3f(viewport[2], 0, 0)
        glEnd()

        glEnable(GL_DEPTH_TEST)

        glDisable(GL_TEXTURE_2D)
        glPopMatrix()

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()

        glMatrixMode(GL_MODELVIEW)

    def draw_tools(self, picking=False):
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        viewport = glGetIntegerv( GL_VIEWPORT )
        glOrtho(0.0, viewport[2], 0.0, viewport[3], -1.0, 1.0)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()

        sW = viewport[2] * 1.0
        sH = viewport[3] * 1.0

        glLoadIdentity()
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)

        glEnable(GL_BLEND)
        glColor3f(1,1,1)

        size = 45.

        coef_sH = 50
        coef_sW = 50

        for tool in self.tools:
            position_x = sW - abs(tool.position[0]) if tool.position[0] < 0 else tool.position[0]
            position_y = sH - abs(tool.position[1]) if tool.position[1] < 0 else tool.position[1]

            coef_sW = tool.size[0]
            coef_sH = tool.size[1]

            if picking:
                glColor3ub(tool.color_id[0], tool.color_id[1], tool.color_id[2])
                glEnable(GL_TEXTURE_2D)
                glBindTexture(GL_TEXTURE_2D, self.tool_background)
            else:
                glColor3f(1,1,1)
                glEnable(GL_TEXTURE_2D)
                glBindTexture(GL_TEXTURE_2D, tool.texture)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0)
            glVertex3f(position_x, position_y, 0)
            glTexCoord2f(0, 1)
            glVertex3f(position_x, (position_y + coef_sH), 0)
            glTexCoord2f(1, 1)
            glVertex3f((position_x + coef_sW), (position_y + coef_sH), 0)
            glTexCoord2f(1, 0)
            glVertex3f((position_x + coef_sW), position_y, 0)
            glEnd()

            if tool.pressed and not picking:
                glDisable(GL_TEXTURE_2D)
                glColor3f(1.,.0,.0)
                glLineWidth(2.)
                glBegin(GL_LINE_LOOP)
                glVertex3f(position_x, position_y, 0)
                glVertex3f(position_x, (position_y + coef_sH), 0)
                glVertex3f((position_x + coef_sW), (position_y + coef_sH), 0)
                glVertex3f((position_x + coef_sW), position_y, 0)
                glEnd()


        glEnable(GL_DEPTH_TEST)

        glDisable(GL_TEXTURE_2D)
        glPopMatrix()

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()

        glMatrixMode(GL_MODELVIEW)


    def normalize_angle(self, angle):
        while angle < 0:
            angle += 360 * 16
        while angle > 360 * 16:
            angle -= 360 * 16
        return angle

    def normalize_angle_x(self, angle):
        if angle < -90*16:
            angle = -90*16
        if angle > 90*16:
            angle = 90*16
        return angle


def _gl_vector(array, *args):
    '''
    Convert an array and an optional set of args into a flat vector of GLfloat
    '''
    array = numpy.array(array)
    if len(args) > 0:
        array = numpy.append(array, args)
    vector = (GLfloat * len(array))(*array)
    return vector