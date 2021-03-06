from django.shortcuts import render_to_response, get_object_or_404
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.template import RequestContext
from django.utils import simplejson
from django.db.models import Avg
from models import *
#from bioversity.utils import _get_elementos
from diversity.forms import DiversityForm, PrecioForm
from diversity.decorators import session_required
from biodiversity.utils import MESES 
from biodiversity import grafos 

def list_parse(s):
    for c in ['[', ']', 'u', "'",]:
        s = s.replace(c,'')
    return s.split(',')

@session_required
def _get_params(request):
    '''Sacar de la variable de sesion y formar queryset''' 
    params = {'fecha__year': request.session['fecha'], 
              'producto': request.session['producto']
             }

    return params

def index(request):
    '''Vista incluye formulario de consulta'''
    paises = Pais.objects.all()
    if request.method == 'POST':
        form = PrecioForm(request.POST)
        if form.is_valid():
            request.session['lugares'] = form.cleaned_data['lugar'].values_list('id', flat=True)
            request.session['fecha'] = form.cleaned_data['fecha']
            #request.session['pais'] = form.cleaned_data['fecha']
            request.session['producto'] = form.cleaned_data['producto']
            #Unidad no se mete al params.
            request.session['unidad'] = form.cleaned_data['unidad']
            request.session['activa'] = True
            activa = True
            return HttpResponseRedirect('/precio/grafo/productor/')
        else:
            activa = False
        dicc = {'form': form, 'activa': activa, 'paises': paises}
        return render_to_response('precio/index.html', dicc,
                                  context_instance = RequestContext(request))
    else:
        form = PrecioForm()
        return render_to_response('precio/index.html', 
                                  {'form': form, 'paises': paises},
                                  context_instance = RequestContext(request))

@session_required
def grafo(request, tipo):
    '''Grafo generado del precio'''
    leyendas = []
    models = dict(productor = Precio, consumidor=PrecioConsumidor)
    moneda = None 
    unidad = None
    if tipo in models.keys():
        filas = []
        params = _get_params(request)
        
        #linea mas larga ever
        normalizar = True if len(request.session['lugares']) >1 or request.session['unidad']!='nativa' else False 
        
        for zona in request.session['lugares']:
            valores = []
            leyenda = Lugar.objects.get(pk=zona).nombre
            leyendas.append(leyenda)
            params['zona'] = zona
            for mes in range(1, 13):
                params['fecha__month'] = mes
                if normalizar==False:
                    precio = models[tipo].objects.filter(**params).aggregate(valor = Avg('precio_%s' % tipo))['valor']
                    if not unidad:
                        try: 
                            unidad = models[tipo].objects.filter(**params)[0].unidad.nombre
                        except:
                            pass
                    if not moneda:
                        try:
                            moneda = models[tipo].objects.filter(**params)[0].moneda.nombre 
                        except:
                            pass
                        #codigo no corerra nunca pero mejor lo dejo LOL
                        #for coso in models[tipo].objects.filter(**params):
                        #    if coso.moneda.nombre:
                        #        moneda = coso.moneda.nombre
                        #        break
                else:
                    #sacamos un promedio de lo internacional a manopla
                    moneda = 'Dolar'
                    total = 0
                    for objeto in  models[tipo].objects.filter(**params):
                        total += objeto.to_int()[0]
                        if not unidad:
                            try:
                                unidad = objeto.unidad.unidad_int.nombre
                            except:
                                pass
                    try:
                        precio = total/models[tipo].objects.filter(**params).count() 
                    except: 
                        precio = 0
                    
                valores.append(float(precio)) if precio != None else valores.append(0)
            fila = {'leyenda': leyenda, 'valores': valores}
            filas.append(fila)
        return render_to_response('precio/%s.html' % tipo,
                                  {'tiempos': MESES,
                                  'filas': filas,
                                  'moneda': moneda,
                                  'unidad': unidad,
                                  'leyendas': leyendas,
                                  'tipo':tipo},
                                  context_instance = RequestContext(request))
    else:
        raise Http404

def grafos_ajax(request, tipo):
    leyendas = []
    models = dict(productor = Precio, consumidor=PrecioConsumidor)
    if tipo in models.keys():
        filas = []
        filas_grafo = []
        params = {} 

        for lugar in Lugar.objects.all():
            valores = []
            leyendas.append(lugar.nombre)
            params['zona'] = lugar 
            for mes in range(1, 13):
                params['fecha__month'] = mes
                total = 0
                for objeto in  models[tipo].objects.filter(**params):
                    total += objeto.to_int()[0]
                try:
                    precio = total/models[tipo].objects.filter(**params).count() 
                except: 
                    precio = 0
                valores.append(float(precio)) if precio != None else valores.append(0)
            filas_grafo.append(valores)
        json = simplejson.dumps(dict(filas=filas_grafo, leyendas=leyendas, 
                                     titulo='Precio del Banano al %s' % tipo, 
                                     labels = MESES, units = ['mes', '$']))
        return HttpResponse(json, mimetype='application/javascript') 
    else:
        raise Http404
