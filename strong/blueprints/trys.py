from flask import Blueprint, render_template
from flask_socketio import emit
from strong import socketio


try_bp = Blueprint('try', __name__)  # 静态资源和模板文件夹应该有默认值


@try_bp.route('/') 
def chat():
    return render_template('try/chat.html')


@socketio.on('new_message')
def new_message(m):
    print(f'[socket] {m}')
    from datetime import datetime
    add = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    emit('new_message', {'m': f'{add}: {m}'}, broadcast=True)  # broadcast:广播
    