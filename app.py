from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flasgger import Swagger, swag_from
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os


# Configuración de la aplicación
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///survey.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY') or 'your_secret_key'

swagger = Swagger(app)

# Inicialización de la base de datos
db = SQLAlchemy(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

# Modelos de la base de datos
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(10), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Survey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('survey.id'), nullable=False)
    survey = db.relationship('Survey', backref=db.backref('questions', lazy=True))
    question_text = db.Column(db.Text, nullable=False)

class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    question = db.relationship('Question', backref=db.backref('options', lazy=True))
    option_text = db.Column(db.String(200), nullable=False)

class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    survey_id = db.Column(db.Integer, db.ForeignKey('survey.id'), nullable=False)
    survey = db.relationship('Survey', backref=db.backref('responses', lazy=True))
    user = db.relationship('User', backref=db.backref('responses', lazy=True))
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey('response.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    selected_option_id = db.Column(db.Integer, db.ForeignKey('option.id'), nullable=False)
    response = db.relationship('Response', backref=db.backref('answers', lazy=True))
    question = db.relationship('Question', backref=db.backref('answers', lazy=True))
    selected_option = db.relationship('Option', backref=db.backref('answers', lazy=True))

# Ruta para crear encuestas con preguntas y opciones
@app.route('/create-surveys', methods=['POST'])
def create_surveys():
    survey_titles = [
        "Satisfacción del Cliente",
        "Preferencias de Productos",
        "Uso de Redes Sociales",
        "Opiniones sobre el Servicio al Cliente",
        "Evaluación de la Experiencia de Compra",
        "Encuesta de Salud y Bienestar",
        "Preferencias de Entretenimiento",
        "Hábitos de Consumo",
        "Opinión sobre Nuevos Productos",
        "Encuesta sobre Tendencias de Tecnología"
    ]
    
    question_texts = [
        "¿Qué tan satisfecho estás con nuestro producto?",
        "¿Con qué frecuencia usas nuestro servicio?",
        "¿Recomendarías nuestro producto a otros?",
        "¿Cómo calificarías nuestra atención al cliente?",
        "¿Cuál es tu principal fuente de entretenimiento?",
        "¿Cuánto tiempo dedicas al ejercicio semanalmente?",
        "¿Qué tan probable es que compres un producto nuevo de nuestra marca?",
        "¿Cuáles son tus principales preocupaciones al comprar en línea?",
        "¿Qué tan a menudo actualizas tus dispositivos tecnológicos?",
        "¿Cuál es tu red social favorita?"
    ]
    
    option_texts = [
        ["Muy satisfecho", "Satisfecho", "Neutral", "Insatisfecho"],
        ["Diariamente", "Semanalmente", "Mensualmente", "Raramente"],
        ["Definitivamente sí", "Probablemente sí", "No estoy seguro", "Probablemente no"],
        ["Excelente", "Bueno", "Regular", "Malo"],
        ["Televisión", "Streaming", "Lectura", "Juegos"],
        ["Menos de 1 hora", "1-3 horas", "3-5 horas", "Más de 5 horas"],
        ["Muy probable", "Probable", "Poco probable", "Nada probable"],
        ["Seguridad", "Precio", "Calidad", "Entrega"],
        ["Cada año", "Cada 2-3 años", "Cada 4-5 años", "Menos frecuentemente"],
        ["Facebook", "Instagram", "Twitter", "TikTok"]
    ]
    
    for i, title in enumerate(survey_titles):
        # Crear la encuesta
        survey_description = f"Por favor, complete la encuesta '{title}' para ayudarnos a mejorar nuestros servicios."
        new_survey = Survey(title=title, description=survey_description)
        db.session.add(new_survey)
        db.session.commit()

        # Crear las preguntas y opciones para cada encuesta
        for j, question_text in enumerate(question_texts):
            new_question = Question(survey_id=new_survey.id, question_text=question_text)
            db.session.add(new_question)
            db.session.commit()

            # Crear las opciones para cada pregunta
            for option_text in option_texts[j]:
                new_option = Option(question_id=new_question.id, option_text=option_text)
                db.session.add(new_option)

        db.session.commit()

    return jsonify({"message": "10 encuestas creadas con éxito"}), 201


# Rutas para usuarios
@app.route('/register', methods=['POST'])
@swag_from({
    'summary': 'Registrar un nuevo usuario.',
    'description': 'Registra un nuevo usuario con username, password, email y rol.',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'username': {'type': 'string'},
                    'password': {'type': 'string'},
                    'email': {'type': 'string'},
                    'role': {'type': 'string', 'enum': ['user', 'admin']}
                }
            }
        }
    ],
    'responses': {
        201: {
            'description': 'Usuario registrado exitosamente.'
        },
        400: {
            'description': 'El username ya existe.'
        }
    }
})
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    role = data.get('role')

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Username already exists"}), 400

    new_user = User(username=username, email=email, role=role)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201

@app.route('/login', methods=['POST'])
@swag_from({
    'summary': 'Iniciar sesión.',
    'description': 'Autentica un usuario y retorna un token JWT.',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'username': {'type': 'string'},
                    'password': {'type': 'string'}
                }
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Inicio de sesión exitoso. Devuelve un token JWT.'
        },
        401: {
            'description': 'Credenciales inválidas.'
        }
    }
})
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if user is None or not user.check_password(password):
        return jsonify({"message": "Invalid credentials"}), 401

    access_token = create_access_token(identity={'username': user.username, 'role': user.role})
    return jsonify(access_token=access_token), 200

# Rutas para encuestas y respuestas
@app.route('/surveys', methods=['GET'])
@swag_from({
    'summary': 'Obtener encuestas activas.',
    'description': 'Retorna una lista de encuestas activas.',
    'responses': {
        200: {
            'description': 'Lista de encuestas activas.'
        }
    }
})
def get_surveys():
    surveys = Survey.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': survey.id,
        'title': survey.title,
        'description': survey.description,
        'is_active': survey.is_active
    } for survey in surveys])

@app.route('/surveys', methods=['POST'])
@jwt_required()
def create_survey():
    data = request.get_json()
    title = data.get('title')
    description = data.get('description')

    new_survey = Survey(title=title, description=description)
    db.session.add(new_survey)
    db.session.commit()

    return jsonify({"message": "Survey created successfully"}), 201

@app.route('/questions', methods=['GET'])
@swag_from({
    'summary': 'Obtener preguntas con filtros.',
    'description': 'Obtiene preguntas filtradas por survey_id y/o question_text.',
    'parameters': [
        {'name': 'survey_id', 'in': 'query', 'type': 'integer'},
        {'name': 'question_text', 'in': 'query', 'type': 'string'}
    ],
    'responses': {
        200: {
            'description': 'Lista de preguntas filtradas.'
        }
    }
})
def get_questions():
    survey_id = request.args.get('survey_id')
    question_text = request.args.get('question_text')

    query = Question.query

    if survey_id:
        query = query.filter_by(survey_id=survey_id)

    if question_text:
        query = query.filter(Question.question_text.ilike(f"%{question_text}%"))

    questions = query.all()

    return jsonify([{
        'id': question.id,
        'survey_id': question.survey_id,
        'question_text': question.question_text
    } for question in questions])

@app.route('/questions', methods=['POST'])
@jwt_required()
@swag_from({
    'summary': 'Crear una nueva pregunta para una encuesta.',
    'description': 'Crea una nueva pregunta asociada a una encuesta existente.',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'survey_id': {'type': 'integer', 'description': 'ID de la encuesta a la que pertenece la pregunta.'},
                    'question_text': {'type': 'string', 'description': 'Texto de la pregunta.'}
                },
                'required': ['survey_id', 'question_text']
            }
        }
    ],
    'responses': {
        201: {
            'description': 'Pregunta creada exitosamente.'
        },
        400: {
            'description': 'Solicitud incorrecta. Posible falta de parámetros obligatorios.'
        }
    }
})
def create_question():
    data = request.get_json()
    survey_id = data.get('survey_id')
    question_text = data.get('question_text')

    new_question = Question(survey_id=survey_id, question_text=question_text)
    db.session.add(new_question)
    db.session.commit()

    return jsonify({"message": "Question created successfully"}), 201

@app.route('/options', methods=['GET'])
@swag_from({
    'summary': 'Obtener opciones con filtros.',
    'description': 'Obtiene opciones filtradas por question_id y/o option_text.',
    'parameters': [
        {'name': 'question_id', 'in': 'query', 'type': 'integer'},
        {'name': 'option_text', 'in': 'query', 'type': 'string'}
    ],
    'responses': {
        200: {
            'description': 'Lista de opciones filtradas.'
        }
    }
})
def get_options():
    question_id = request.args.get('question_id')
    option_text = request.args.get('option_text')

    query = Option.query

    if question_id:
        query = query.filter_by(question_id=question_id)

    if option_text:
        query = query.filter(Option.option_text.ilike(f"%{option_text}%"))

    options = query.all()

    return jsonify([{
        'id': option.id,
        'question_id': option.question_id,
        'option_text': option.option_text
    } for option in options])

@app.route('/options', methods=['POST'])
@jwt_required()
@swag_from({
    'summary': 'Crear una nueva opción para una pregunta.',
    'description': 'Crea una nueva opción de respuesta asociada a una pregunta existente.',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'question_id': {'type': 'integer', 'description': 'ID de la pregunta a la que pertenece la opción.'},
                    'option_text': {'type': 'string', 'description': 'Texto de la opción de respuesta.'}
                },
                'required': ['question_id', 'option_text']
            }
        }
    ],
    'responses': {
        201: {
            'description': 'Opción creada exitosamente.'
        },
        400: {
            'description': 'Solicitud incorrecta. Posible falta de parámetros obligatorios.'
        }
    }
})
def create_option():
    data = request.get_json()
    question_id = data.get('question_id')
    option_text = data.get('option_text')

    new_option = Option(question_id=question_id, option_text=option_text)
    db.session.add(new_option)
    db.session.commit()

    return jsonify({"message": "Option created successfully"}), 201

@app.route('/responses', methods=['GET'])
@swag_from({
    'summary': 'Obtener respuestas con filtros.',
    'description': 'Obtiene respuestas filtradas por survey_id, user_id, y/o submitted_at.',
    'parameters': [
        {'name': 'survey_id', 'in': 'query', 'type': 'integer'},
        {'name': 'user_id', 'in': 'query', 'type': 'integer'},
        {'name': 'submitted_at', 'in': 'query', 'type': 'string', 'format': 'date-time'}
    ],
    'responses': {
        200: {
            'description': 'Lista de respuestas filtradas.'
        }
    }
})
def get_responses():
    survey_id = request.args.get('survey_id')
    user_id = request.args.get('user_id')
    submitted_at = request.args.get('submitted_at')

    query = Response.query

    if survey_id:
        query = query.filter_by(survey_id=survey_id)

    if user_id:
        query = query.filter_by(user_id=user_id)

    if submitted_at:
        query = query.filter(Response.submitted_at.like(f"%{submitted_at}%"))

    responses = query.all()

    return jsonify([{
        'id': response.id,
        'user_id': response.user_id,
        'survey_id': response.survey_id,
        'submitted_at': response.submitted_at
    } for response in responses])


@app.route('/responses', methods=['POST'])
@jwt_required()
@swag_from({
    'summary': 'Enviar una respuesta a una encuesta.',
    'description': 'Envía una respuesta a una encuesta y guarda las opciones seleccionadas.',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'survey_id': {'type': 'integer'},
                    'answers': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'question_id': {'type': 'integer'},
                                'selected_option_id': {'type': 'integer'}
                            }
                        }
                    }
                }
            }
        }
    ],
    'responses': {
        201: {
            'description': 'Respuesta enviada exitosamente.'
        }
    }
})
def submit_response():
    data = request.get_json()
    survey_id = data.get('survey_id')
    answers = data.get('answers')

    user_identity = get_jwt_identity()
    user = User.query.filter_by(username=user_identity['username']).first()

    new_response = Response(user_id=user.id, survey_id=survey_id)
    db.session.add(new_response)
    db.session.commit()

    for answer_data in answers:
        question_id = answer_data['question_id']
        selected_option_id = answer_data['selected_option_id']

        new_answer = Answer(response_id=new_response.id, question_id=question_id, selected_option_id=selected_option_id)
        db.session.add(new_answer)

    db.session.commit()

    return jsonify({"message": "Response submitted successfully"}), 201

if __name__ == '__main__':
    app.run(debug=True)
