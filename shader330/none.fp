#version 330 core
in vec3 attrib_Fragment_Color;
out vec4 color;

void main(){
  color = vec4(attrib_Fragment_Color, 1.0);
}