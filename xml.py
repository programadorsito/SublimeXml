import sublime, random, re, os
import sublime_plugin





class TiposXml:
	def tipoValido(tipo):
		return tipo.startswith("text.zul ") or tipo.startswith("text.html") or tipo.startswith("text.maven")

class CompletacionXml:
	def __init__(self, tipo=None):
		if not tipo:tipo=sublime.active_window().active_view().scope_name(0)
		if not TiposXml.tipoValido(tipo):return
		if tipo.startswith("text.zul "):self.tipo="zul"
		elif tipo.startswith("text.html"):self.tipo="html"
		elif tipo.startswith("text.android "):self.tipo="android"
		elif tipo.startswith("text.hibernate "):self.tipo="hbm"
		elif tipo.startswith("text.maven"):self.tipo="maven"
		self.rutaArchivo=sublime.packages_path()+os.sep+"SublimeXml"+os.sep+"%s.json"%(self.tipo)
		self.cargar()
	
	def cargar(self):
		d=sublime.decode_value(open(self.rutaArchivo).read())
		if not d:d={}
		self.tags=d["tags"] if d.get("tags") else {}
		self.attrs=d["attrs"] if d.get("attrs") else {}

	def agregarActuales(self):
		view=sublime.active_window().active_view()
		self.lineas=view.substr(sublime.Region(0, view.size())).splitlines()
		for l in self.lineas:
			l=l.strip()
			if not l:continue
			if l.startswith("<") and not l.startswith("</"):
				self.agregarTag(l)
		self.guardar()

	def agregarTag(self, l):
		tag=l[1:l.find(" ")].strip() if l.find(" ")!=-1 and l.find(" ")<l.find(">") else l[1:l.find(">")] 
		if not self.tags.get(tag):self.tags[tag]={"n":tag, "c":l[1:], "s":"n"}
		elif not self.tags[tag]["s"]=="n":self.tags[tag]["c"]=l[1:]
		attr=""
		tempo=""
		colectando=False
		ignorar=False
		for c in l:
			if c.isalnum() or c==':':tempo+=c
			elif not ignorar and c=="'":ignorar=True	
			elif ignorar and c!="'":continue
			elif ignorar and c=="'":
				self.agregarAtributo(tag, attr.strip(), "")
				attr=""
				tempo=""
				ignorar=False
			elif not colectando and c=='"':colectando=True
			elif colectando and c=='"':
				if tempo.strip().find(" ")!=-1:tempo=""
				self.agregarAtributo(tag, attr.strip(), tempo.strip())
				attr=""
				tempo=""
				colectando=False
			elif colectando:
				tempo+=c
				continue
			elif c=="=":
				attr=tempo
				tempo=""
			elif c==" ":tempo=""

				

	def agregarAtributo(self, tag, attr, valor):
		coma=""
		if not self.attrs.get(attr):self.attrs[attr]={"n":attr, "e":tag, "v":valor}
		elif valor:
			if not valor in self.attrs[attr]["v"].strip().split(","):
				if self.attrs[attr]["v"].strip():coma=","
				self.attrs[attr]["v"]+=coma+valor
				coma=""
		if not tag in self.attrs[attr]["e"].strip().split(","):
			if self.attrs[attr]["e"].strip():coma=","
			self.attrs[attr]["e"]+=coma+tag


	def guardar(self):
		archivo=open(self.rutaArchivo, "w")
		d={}
		d["tags"]=self.tags
		d["attrs"]=self.attrs
		archivo.write(sublime.encode_value(d, True))
		archivo.close()

	def valores(self, atributo):
		atributo=atributo.strip()
		lista=[]
		valores=self.attrs[atributo]["v"].split(",")
		for v in valores:lista.append((v+"\t•", v))
		return lista
		
	def atributos(self, etiqueta):
		lista=[]
		for a in self.tags[etiqueta]["attrs"]:lista.append((a["n"]+"\t•", a["n"]+"="+'"${1:}"'))
		return lista

	def etiquetas(self):
		lista=[]
		for e in self.tags:
			tag=self.tags[e]
			
			if tag["c"].count("\n")<=1:
				clean=tag["c"].strip()
				if not clean.endswith("/>") and not re.findall(">[^<]*<", clean) and clean.endswith(">"):tag["c"]+="\n\n</"+tag["n"]+">\n"
			lista.append((e+"\t•", self.agregarCursores(tag["c"])))
		return lista

	def agregarCursores(self, texto):
		#return texto
		lineas=texto.splitlines()
		i=1
		colectando=False
		bloque=""
		for l in lineas:
			l=l.replace('="', '="${').replace('" ', '}" ').replace('"/', '}"/').replace('">', '}">')
			linea=""
			anterior=""
			for c in l:
				linea+=c
				if c=="{" and anterior=="$":linea+=str(i)+":"
				i+=1
				anterior=c
			bloque+=linea+"\n"
		return bloque

	def limpiarCursores(self, linea):
		coincidencias=self.patron.findall(linea)
		for coincidencia in coincidencias:
			quitar=coincidencia[:coincidencia.find(":")+1]
			linea=linea.replace(coincidencia, coincidencia.replace(quitar, "").replace("}", ""))
		return linea

	def grabar(self, texto):
		lineas=texto.splitlines()
		tag=lineas[0].strip()
		tag=tag[1:tag.find(" ")]
		bloque=""
		for l in lineas:
			clean=l.strip()
			if not clean:bloque+="\n"
			if clean.startswith("<") or clean.startswith("</"):bloque+=l+"\n"
		bloque=bloque.strip()[1:]
		if not self.tags.get(tag):self.tags[tag]={"n":tag, "c":bloque}
		else:self.tags[tag]["c"]=bloque
		self.tags[tag]["s"]="y"
		self.guardar()

	def completar(self):
		view=sublime.active_window().active_view()
		linea=view.substr(sublime.Region(view.line(view.sel()[0]).a, view.sel()[0].a))
		if linea.rfind(">")>linea.rfind("<"):return
		if linea.find("<")==-1:return
		etiqueta=linea[linea.rfind("<")+1:linea.find(" ", linea.rfind("<"))]
		etiqueta=etiqueta.strip()
		if not etiqueta:
			return sorted(self.etiquetas())
		elif linea.strip().endswith("=") or linea.strip().endswith('="'):
			return sorted(self.valores(linea[linea.rfind(" "):linea.rfind("=")]))
		else:
			return sorted(self.atributos(etiqueta))

	def getAtributos(self, etiqueta):
		lista=[]
		for atributo in self.attrs:
			if etiqueta in self.attrs[atributo]["e"].split(","):
				lista.append(atributo)
		return lista


class xmlCompletions(sublime_plugin.EventListener):
	def on_query_completions(self, view, prefix, locations):
		tipo=view.scope_name(0)
		if TiposXml.tipoValido(tipo):
			punto=view.sel()[0].a
			completacion=CompletacionXml(tipo)
			if view.substr(sublime.Region(punto-1, punto))=="<":
				return completacion.completar()
			else:
				linea=view.substr(sublime.Region(view.line(punto).a, punto))
				if linea.find("<")==-1:return
				if linea.find(">")!=-1:return
				linea=linea[linea.rfind("<"):]
				if linea.endswith(" "):
					etiqueta=linea[1:linea.find(" ")]
					return [(atributo+"\t•", atributo+'="${1:}"')for atributo in completacion.getAtributos(etiqueta)]
				elif linea.endswith('="'):
					atributo=linea[linea.rfind(" ")+1:linea.rfind("=")].strip()
					return completacion.valores(atributo)

				
class Expresion:
	def __init__(self, exp, etiquetas):
		self.etiquetas=etiquetas
		self.generarDiccionario(exp)
		self.keys=self.etiquetas.keys()
		
	def generarDiccionario(self, exp):
		exp=exp.strip()+"^"
		self.diccionario={}
		self.nivel=1
		self.diccionario[self.nivel]=[]
		tag=""
		texto=""
		atributos=[]
		atributo=""
		bloqueo=0
		colectandoNumero=False
		colectandoTexto=False
		colectandoAtributo=False
		numero=""
		comprimido=""
		for c in exp:
			if c=="[":
				colectandoAtributo=True
				continue
			elif colectandoAtributo and c=="]":
				if atributo:
					atributos.append(atributo)
					atributo=""
				colectandoAtributo=False
				continue
			elif colectandoAtributo:
				atributo+=c
				continue
			elif c=="{":
				colectandoTexto=True
				continue
			elif colectandoTexto and c=="}":
				colectandoTexto=False
				continue
			elif colectandoTexto:
				texto+=c
				continue
			elif c=="(":
				bloqueo+=1
				continue
			elif c==")":
				bloqueo-=1
				if bloqueo==0:
					self.diccionario[self.nivel].append(Expresion(comprimido, self.etiquetas))
			if bloqueo==0:
				if colectandoNumero and c.isdigit():
					numero+=c
				elif colectandoNumero:

					for i in range(int(numero)):
						atributosTemp=[]
						if atributos:
							for a in atributos:atributosTemp.append(a.replace("$i", str(i+1)))
						self.diccionario[self.nivel].append(self.newTag(tag, texto.replace("$i", str(i+1)), atributosTemp))
					numero=""
					tag=""
					texto=""
					atributos=[]
					colectandoNumero=False

				if c==">":
					if tag:self.diccionario[self.nivel].append(self.newTag(tag, texto, atributos))
					tag=""
					texto=""
					atributos=[]
					self.nivel+=1
					self.diccionario[self.nivel]=[]
				elif c=="+" and tag:
					self.diccionario[self.nivel].append(self.newTag(tag, texto, atributos))
					tag=""
					texto=""
					atributos=[]
				elif c=="*":colectandoNumero=True
				elif c=="^":
					if tag:self.diccionario[self.nivel].append(self.newTag(tag, texto, atributos))
					break
				elif c.isalpha():tag+=c
			else:
				comprimido+=c
		return self.diccionario

	def newTag(self, tag, texto, atributos):
		return {"nombre":tag, "texto":texto, "atributos":atributos}

	def generarCompletacion(self, deltaTab=0):
		i=self.nivel
		completacionUltimoNivel=""
		completacionNivelActual=""
		while i>=1:
			for t in self.diccionario[i]:
				if type(t)==type({}):
					completacionNivelActual+=self.obtenerCompletacion(t, completacionUltimoNivel, i-1+deltaTab)
				else:completacionNivelActual+=t.generarCompletacion(i-1)
			completacionUltimoNivel=completacionNivelActual
			completacionNivelActual=""
			i-=1
		return completacionUltimoNivel
		
	#toma el inici y el final de la etiqueta y la inserta en el medio
	def obtenerCompletacion(self, tag, medio, tab):
		tab="\t"*tab
		atributos=""
		if tag["texto"]:
			if tag["texto"].find("lorem")!=-1:tag["texto"]=self.lorem(int(tag["texto"].replace("lorem", "").strip()))
			tag["texto"]="\n\t"+tab+tag["texto"]
		if tag["atributos"]:
			for a in tag["atributos"]:atributos+=a+" "

		return self.generarEtiqueta(tag["nombre"])%{"tag":tag["nombre"], "texto":tag["texto"], "medio":medio, "tab":tab, "atributos":atributos}
	
	def generarEtiqueta(self, etiqueta):
		tag=None
		etiqueta=etiqueta.strip()
		if self.etiquetas:
			if self.etiquetas.get(etiqueta):
				tag=self.etiquetas[etiqueta]
		if tag:
			inicio=""
			medio=""
			fin=""
			cuerpo=[]
			lineas=tag["c"].splitlines()
			for l in lineas:
				if l.strip():cuerpo.append(l)
			inicio=cuerpo[0].strip()
			if inicio.endswith("/>"):return "%(tab)s<"+inicio.replace("/>", " %(atributos)s/>\n")
			else:
				inicio="%(tab)s<"+inicio.replace(">", " %(atributos)s>")
				inicio+="%(texto)s\n"
				medio+="%(medio)s\n"
				fin="%(tab)s</"+etiqueta+">\n"
			return inicio+medio+fin
		else:
			return """%(tab)s<%(tag)s %(atributos)s>%(texto)s
%(medio)s
%(tab)s</%(tag)s>
"""

	def lorem(self, n):
		texto=""
		for i in range(n):texto+=chr(random.randint(97,122))
		return texto.replace(chr(random.randint(97,122)), " ").replace(chr(random.randint(97,122)), " ")
	
class emmetCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		view=sublime.active_window().active_view()
		completacion=CompletacionXml()
		if view.sel()[0].a!=view.sel()[0].b:
			completacion.grabar(view.substr(view.sel()[0]))
			return
		self.etiquetas=completacion.tags
		linea=view.substr(sublime.Region(view.line(view.sel()[0]).a, view.sel()[0].a))
		contadorTabs=linea.count("\t")
		linea=linea.strip()
		punto=view.line(view.sel()[0].a).a
		texto=""
		if linea.startswith("lorem"):texto=self.lorem(int(linea.replace("lorem", "")))
		elif linea.isalpha():texto=self.bloqueUnico(linea, contadorTabs)
		else:
			exp=Expresion(linea, self.etiquetas)
			texto=exp.generarCompletacion()
		view.erase(edit, view.line(punto))
		view.run_command('insert_snippet', {"contents": texto})

	def lorem(self, n):
		texto=""
		for i in range(n):texto+=chr(random.randint(97,122))
		return texto.replace(chr(random.randint(97,122)), " ").replace(chr(random.randint(97,122)), " ")

	def bloqueUnico(self, tag, contadorTabs):
		tab="\t"*contadorTabs
		return """%(tab)s<%(tag)s>
%(tab)s
%(tab)s</%(tag)s>"""%{"tag":tag, "tab":tab}

class CargadorInteligente(sublime_plugin.EventListener):
	def on_post_save(self, view):
		tipo=view.scope_name(0)
		if TiposXml.tipoValido(tipo):
			CompletacionXml().agregarActuales()
