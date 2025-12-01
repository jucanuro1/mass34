import io
import json
from datetime import date, datetime, timedelta, time
from django.conf import settings
from django.utils.timezone import make_aware, get_current_timezone
import locale
from django.shortcuts import redirect
from random import choice, randint
from django.core.exceptions import ObjectDoesNotExist
from .utils.whatsapp_api import enviar_mensaje_whatsapp

import pandas as pd
import re
from openpyxl.utils import get_column_letter

from django.db.models.functions import TruncDate

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.template.loader import render_to_string

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from django.db import IntegrityError, DatabaseError, OperationalError
from django.db import models
from django.db import transaction
from django.db.models.functions import Cast
from django.db.models import Q, Count, Max, Prefetch, OuterRef, Subquery, When, Case, Exists, DateField, F, FloatField, ExpressionWrapper, IntegerField

from django.http import JsonResponse, HttpResponse, HttpResponseForbidden, HttpResponseBadRequest, HttpRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from django.views.generic import View, DetailView, ListView, TemplateView
from django.db.models.functions import ExtractYear, ExtractMonth
from django.utils.formats import date_format
import platform

from .models import (
    Candidato, Proceso, Empresa, Sede, Supervisor, 
    RegistroAsistencia, DatosCualificacion, ComentarioProceso, 
    RegistroTest, MOTIVOS_DESCARTE, DocumentoCandidato, TipoDocumento, TareaEnvioMasivo, MensajePlantilla, DetalleEnvio
)
