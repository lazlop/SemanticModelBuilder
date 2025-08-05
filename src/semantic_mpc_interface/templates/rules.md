Entities represent equipment or spaces in a model - things with properties.
Values are points
relations are how things are related
Templates should optionally describe everything the user expects they be related with, using relations
Values should have name and value naming aligned so for area, the parameters are 'area_name' and 'area_value'
use _ to separate things within a template. 
map name to the name of the template_name. 

We build upon these conventions to simplify use of surveys, code to assemble templates, etc. 

For survey generation, optional parameters will get their own surveys since their cardinality is unkown (maybe)

I thought optional referred to dependencies... I see now that it is args. 

Maybe change from _ to -. This is because when things are inlined a - is used, which means some points use - value. For now, I can just cover both. 

Can't handle connection points. 
Attempted handling connection points as part of the connection, since this matches the cardinality. However, it doesn't really make sense. 

Additionally, this would not be using connection points as they are intended - because I do not in fact know what the connection points of the equipment and zones are, and they have no properties. 