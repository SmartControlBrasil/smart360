from django.shortcuts import render


def demo(request):
    return render(request, "visual_3d/demo.html")


def editor_2d(request):
    return render(request, "visual_3d/editor_2d.html")
