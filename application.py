from flask import Flask, render_template, request, redirect

app = Flask(__name__)

app.vars={}

app.questions = [0,]*3
app.questions[0] = ('How many eyes do you have?', '1','2','3')
app.questions[1] = ('Which fruit do you like best?', 'banana','mango','pineapple')
app.questions[2] = ('Do you like cupcakes?', 'yes','no','maybe')

app.nquestions=len(app.questions)

@app.route('/', methods=['GET', 'POST'])
def main():
    return redirect('/index')

@app.route('/index', methods=['GET', 'POST'])
def first_page():
    nquestions = app.nquestions
    if request.method == 'GET':
        return render_template('userinfo.html', num=nquestions)
    else:
        app.vars['name'] = request.form['name']
        app.vars['age'] = request.form['age']

        with open('{}_{}.txt'.format(app.vars['name'], app.vars['age']), 'w') as f:
            f.write('Name: {}\n'.format(app.vars['name']))
            f.write('Age: {}\n\n'.format(app.vars['age']))

        return redirect('/main')

@app.route('/main')
def main_func():
    if app.questions:
        return redirect('/next')
    else:
        return render_template('end.html')


@app.route('/next', methods=['GET'])
def next_get_question(): #remember the function name does not need to match the URL
    # for clarity (temp variables)
    n = app.nquestions - len(app.questions) + 1
    question = app.questions.pop()
    q_text = question[0]
    a1, a2, a3 = question[1:]

    # save the current question key
    app.currentq = q_text

    return render_template('layout.html', num=n, question=q_text, ans1=a1, ans2=a2, ans3=a3)

@app.route('/next', methods=['POST'])
def next_post_question():  #can't have two functions with the same name
    # Here, we will collect data from the user.
    # Then, we return to the main function, so it can tell us whether to
    # display another question page, or to show the end page.

    with open('{}_{}.txt'.format(app.vars['name'], app.vars['age']), 'a') as f: #a is for append
        f.write('{}\n'.format(app.currentq))
        f.write('{}\n\n'.format(request.form['answer_from_layout'])) #this was the 'name' on layout.html!

    return redirect('/main')

if __name__ == "__main__":
    app.run(debug=True)