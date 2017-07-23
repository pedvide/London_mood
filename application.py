from flask import Flask, render_template, request, redirect, make_response
import datetime
import london_mood

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
        date = request.form['date']
        app.vars['date'] = datetime.date(*[int(part) for part in date.split('/')])
        app.vars['mood'] = london_mood.mood(app.vars['date'])
        return redirect('/results')


@app.route('/results', methods=['GET', 'POST'])
def show_result():
    if request.method == 'GET':
        mood = app.vars['mood']
        average_mood = london_mood.avg_mood_text(mood)
        return render_template('results.html', date=str(app.vars['date']), average_mood=average_mood)
    else:
        return redirect('/index')

@app.route("/plot_mood.png")
def plot_mood():
    from io import BytesIO
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.patches as mpatches

    fig = Figure()
    ax = fig.add_subplot(111)

    barplot = ax.bar([1, 2, 3, 4], app.vars['mood'], bottom=[-0.1, ]*4)
    ax.set_xticks([1, 2, 3, 4])
    ax.set_xticklabels(('Average Mood', 'Twitter', 'News', 'Weather'))
    ax.set_ylim(bottom=-0.1)

    avg_bar = barplot[0]
    mood_text = london_mood.avg_mood_text(app.vars['mood'])
    if mood_text == 'Good':
        avg_bar.set_color('green')
    elif mood_text == 'Meh':
        avg_bar.set_color('yellow')
    else:
        avg_bar.set_color('red')

    for bar in barplot[1:]:
        if bar.get_height() > 0.5:
            bar.set_color('green')
        elif bar.get_height() > 0.0:
            bar.set_color('yellow')
        else:
            bar.set_color('red')

    green_patch = mpatches.Patch(color='green', label='Good')
    yellow_patch = mpatches.Patch(color='yellow', label='Meh')
    red_patch = mpatches.Patch(color='red', label='Bad')
    ax.legend(handles=[green_patch, yellow_patch, red_patch])

    canvas = FigureCanvas(fig)
    png_output = BytesIO()
    canvas.print_png(png_output)
    response = make_response(png_output.getvalue())
    response.headers['Content-Type'] = 'image/png'
    return response


if __name__ == "__main__":
    app.run()