from flask import render_template, request, redirect, flash, url_for, session
from app import webapp
from .MySQL_DB import mysql


@webapp.route('/autoscaler/settings', methods=['GET'])
def auto_scaling_settings():
    return render_template("manager/auto_scaling_settings.html")


@webapp.route('/autoscaler', methods=['GET'])
def auto_scaler():
    upperthres = request.args.get('upperthres')
    lowerthres = request.args.get('lowerthres')
    expandratio = request.args.get('expandratio')
    shrinkratio = request.args.get('shrinkratio')

    cursor = mysql.connection.cursor()
    query = "UPDATE auto_scaler_settings SET upperthres=%s, lowerthres=%s, expandratio=%s, shrinkratio=%s WHERE id = %s"
    cursor.execute(query, (upperthres, lowerthres, expandratio, shrinkratio, 1))
    mysql.connection.commit()
    cursor.close()

    return render_template("manager/auto_scaling_settings.html")
