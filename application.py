from flask import Flask, render_template, request, redirect

app = Flask(__name__)

app.vars={}

mood = 'Good'

@app.route('/', methods=['GET', 'POST'])
def main():
    return redirect('/index')


@app.route('/index', methods=['GET', 'POST'])
def first_page():
    if request.method == 'GET':
        return render_template('userinfo.html')
    else:
        app.vars['date'] = request.form['date']
        return redirect('/result')


@app.route('/results')
def show_result():
    return render_template('results.html', mood=mood)

if __name__ == "__main__":
    app.run()