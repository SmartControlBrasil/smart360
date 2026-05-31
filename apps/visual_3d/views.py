from django.shortcuts import render


def demo(request):
    return render(request, "visual_3d/demo.html")
