from models import Process

def record_status(processname, message=None, percent_done=None):
    try:
        proc_rec = Process.objects.get(name=processname)
    except Process.DoesNotExist:
        proc_rec = Process(name=processname)
    if message:
        proc_rec.statustext = message
    if percent_done:
        proc_rec.percentdone = percent_done
    proc_rec.save()
