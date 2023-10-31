from flask import Blueprint, render_template
from strong.callbacks import login_required

data_bp = Blueprint('data', __name__, static_folder='static', template_folder='templates')

@data_bp.route('/')
@login_required
def data():
    return render_template('data/data.html')
