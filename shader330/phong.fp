#version 330 core

in vec3 FragPos;
in vec3 normal;

uniform float n;
uniform vec3 lightPos[10];
uniform vec3 lightColor;
uniform vec3 attrib_Color;
out vec4 FragColor;

uniform float Ka;
uniform float Kd;
uniform float Ks;

uniform vec3 viewPos;

void main(){
    float a0 = 1.0;
	float a1 = 1.0;
	float a2 = 0.25;

	vec3 result;

	vec3 norm = normalize(normal);
	vec3 viewDir = normalize(viewPos - FragPos);

	vec3 ambient = Ka * attrib_Color;
	result = ambient;

	for(int i = 0; i < n; ++i){
		float distance = length(lightPos[i] - FragPos);
		float attenuation = 1.0 / (a0 + a1 * distance + a2 * (distance * distance));

	    //vec3 ambient = Ka * lightColor;

	    vec3 lightDir = normalize(lightPos[i] - FragPos);

	    vec3 reflectDir = reflect(-lightDir, norm);

	    float diff = max(dot(norm, lightDir), 0.0);
	    vec3 diffuse = Kd * diff * lightColor;

	    float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32);
	    vec3 specular = Ks * spec * lightColor;

	    //ambient  *= attenuation;
		diffuse  *= attenuation;
		specular *= attenuation;

	    result += (diffuse + specular) * attrib_Color;
	}
    FragColor = vec4(result, 1.0);
}