from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class AgendaDemoView(LoginRequiredMixin, TemplateView):
    template_name = 'coaching_agenda.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Agenda de Coaching'
        return context