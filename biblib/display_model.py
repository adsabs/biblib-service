import sadisplay
import models as model

desc = sadisplay.describe([getattr(model, attr) for attr in dir(model)])
open('schema.plantuml', 'w').write(sadisplay.plantuml(desc))
open('schema.dot', 'w').write(sadisplay.dot(desc))

# Or only part of schema
desc = sadisplay.describe([model.User, model.Library])
open('auth.plantuml', 'w').write(sadisplay.plantuml(desc))
open('auth.dot', 'w').write(sadisplay.dot(desc))