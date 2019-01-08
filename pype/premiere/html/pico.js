(function(module,exports,require){var
	uuid=Date.now(),
	modules={},
	updates={},
	paths={},
	env={},
	preprocessors={},
	EXT_JS='.js',EXT_JSON='.json',
	MOD_PREFIX='"use strict";\n',
	MOD_POSTFIX='//# sourceURL=',
	PLACE_HOLDER='return arguments.callee.__proto__.apply(this,arguments)', // prevent closure
	getEnv = function(k){
		return env[k]
	},
	dummyCB=function(){},
	dummyLoader=function(){
		arguments[arguments.length-1]()
	},
	// run the module and register the module output
	define=function(url, func, mute){
		if (modules[url] && !isPlaceHolder(modules[url])) return modules[url]
		var
			ext=getExt(url)||EXT_JS,
			pp=preprocessors[ext]

		if (pp) func=pp(url, func)

		switch(ext){
		case EXT_JS:
			var
				module={exports:{}},
				evt={},
				base,
				getBase=function(k){
					base=getMod(k); return base
				},
				m=func.call(mute?{}:evt,module.exports,getMod,module,define,getBase,pico)||module.exports

			if (base) m=inherit(m,base)
			if ('function' === typeof m) m.extend=extend
			if (evt.load) evt.load(m)
			if (evt.update) updates[url]=[evt.update,m]

			if (!url) return m

			return modules[url]=wrap(modules[url],m)
		case EXT_JSON:
			try{
				return modules[url]=JSON.parse(func)
			} catch(e){
				return console.error(url, e.message)
			}
		default: return modules[url]=func
		}
	},
	dummyPico={run:dummyCB,inherit:dummyCB,reload:dummyCB,parse:dummyCB,define:define,import:dummyCB,export:dummyCB,env:getEnv,ajax:dummyCB},//TODO: proxy
	// call when pico.run done
	ran,importRule,
	schedule= (function(){
		return ('undefined'===typeof requestAnimationFrame) ? function(cb){
			return setTimeout(cb, 100)
		}: requestAnimationFrame
	})(),
	funcBody=function(func){
		return func.substring(func.indexOf('{')+1,func.lastIndexOf('}'))
	},
	getExt=function(url){
		if (!url)return null
		var idx=url.lastIndexOf('.')
		return -1!==idx && -1===url.indexOf('/',idx) ? url.substr(idx) : null
	},
	// link to all deps
	linker=function(deps, cb){
		if (!deps.length) return cb()
		loader(deps.shift(),function(err){
			if (err) return cb(err)
			linker(deps, cb)
		})
	},
	// load files, and execute them based on ext
	loader=function(url,cb){
		modules[url] = modules[url] || pico.import(url) // load node module?
		if (modules[url]) return cb(null, modules[url])

		var
			idx=url.indexOf('/'),
			path=~idx?paths[url.slice(0,idx)]:0,
			fname= path ? url.slice(idx+1) : url

		path=path || paths['~'] || ''

		if (path instanceof Function){
			path(fname, function(err, txt){
				if (err) return cb(err)
				js(url,txt,cb)
			})
		}else{
			pico.ajax('get',path+fname+(getExt(url)?'':EXT_JS),null,null,function(err,state,txt){
				if (4!==state) return
				if (err) return cb(err)
				js(url,txt,cb)
			})
		}
	},
	placeHolder=function(url){
		return Object.defineProperties(Function(PLACE_HOLDER), {
			name:{ value: url },
			i:{ value: uuid }
		})
	},
	isPlaceHolder=function(obj){
		return 'function' === typeof obj && uuid===obj.i
	},
	wrap=function(mod, obj){
		if (!mod || mod===obj) return obj
		if (isPlaceHolder(mod)) mod.prototype=obj.prototype
		mod.__proto__=obj
		return mod
	},
	unwrap=function(obj){
		return isPlaceHolder(obj) ? obj.__proto__ : obj
	},
	extend=function(classMod,staticMod) {
		if (!classMod) return this
		return inherit(classMod, this, staticMod)
	},
	inherit=function(mod1,mod2,mod3){
		var
			child=unwrap(mod1),
			ancestor=unwrap(mod2),
			cType=typeof child,
			aType=typeof ancestor,
			fn, props

		switch(cType){
		case 'function':
			fn=child
			props=child.prototype
			break
		case 'object':
			if (cType===aType){
				child.__proto__=ancestor // dun use wrap, inherit not wrap
				return child
			}
			fn= function(){
				return ancestor.apply(this,arguments)
			}
			props=child
			break
		default: return child
		}
		Object.assign(fn,ancestor,unwrap(mod3))
		switch(aType){
		case 'function':
			fn.prototype=Object.assign(Object.create(ancestor.prototype),props,{constructor: ancestor})
			return fn
		case 'object':
			fn.prototype=Object.assign(Object.create(ancestor),props)
			return fn
		default: return child
		}
	},
	getMod=function(url,cb){
		var mod=modules[url]
		if(void 0===mod){
			if (cb) return loader(url,cb)
			return modules[url]=placeHolder(url)
		}
		cb && setTimeout(cb, 0, null, mod) // make sure consistent async behaviour
		return mod
	},
	// do not run the module but getting the deps and inherit
	compile=function(url,txt,deps,me){
		me=me||dummyPico
		var
			script=url ? MOD_PREFIX+txt+(env.live ? '' : MOD_POSTFIX+url) : txt,
			frequire=function(k){
				if(!modules[k])deps.push(k);return modules[k]
			}

		try{
			var func=Function('exports','require','module','define','inherit','pico',script)
		} catch(e){
			return console.error(url, e.message)
		}

		func.call({}, {},frequire,{},define,frequire,me)
		return func
	},
	// js file executer
	js=function(url,txt,cb){
		cb=cb||dummyCB
		if(modules[url]) return cb(null, modules[url])
		if(EXT_JS !== (getExt(url)||EXT_JS)) return cb(null, define(url,txt))

		var
			deps=[],
			func=compile(url,txt,deps)

		if(url)modules[url]=placeHolder(url)

		linker(deps, function(err){
			if (err) return cb(err)

			cb(null,define(url,func))
		})
	},
	tick=function(timestamp){
		var f
		for (var k in updates) {
			(f = updates[k]) && f[0](f[1], timestamp)
		}
		schedule(tick)
	}

var pico=module[exports]={
	run:function(options,func){
		pico.ajax=options.ajax||pico.ajax
		paths=options.paths||paths
		env=options.env||env
		preprocessors=options.preprocessors||preprocessors
		importRule=options.importRule

		var pp
		for(var url in modules){
			(pp=preprocessors[getExt(url)||EXT_JS]) && (modules[url]=pp(url, modules[url]))
		}

		(options.onLoad||dummyLoader)(function(){
			js(options.name||null,funcBody(func.toString()),function(err,main){
				if (err) return console.error(err)

				main && main()
				ran && ran()

				schedule(tick)
			})
		})
	},
	reload:function(url, script, cb){
		if ('function'===typeof script) cb=script
		cb=cb||dummyCB
		var reattach=function(err, m){
			if (err) return cb(err)
			cb(null, modules[url]=wrap(modules[url], m))
		}
		delete modules[url]
		if (cb===script) loader(url, reattach)
		else js(url, script, reattach)
	},
	parse:js,
	define:define,
	import:function(url){
		if (Array.isArray(importRule) && importRule.some(function(rx){
			return rx.match(url)
		}))
			return require(url)
	},
	export:getMod,
	env:getEnv
}
define('pico/func',function(exports,require,module,define,inherit,pico){
	function callerFormat(_, stack){
		var r = stack[0]
		var trace = []

		for (var i = 0, s; (s = stack[i]); i++){
			trace.push(s.toString())
		}

		return {
			typeName: r.getTypeName(),
			functionName: r.getFunctionName(),
			methodName: r.getMethodName(),
			fileName: r.getFileName(),
			line: r.getLineNumber(),
			column: r.getColumnNumber(),
			evalOrigin: r.getEvalOrigin(),
			isTopLevel: r.isToplevel(),
			isEval: r.isEval(),
			isNative: r.isNative(),
			isConstructor: r.isConstructor(),
			trace: trace
		}
	}

	return {
		reflect: function callee(func, limit){
			var orgPrepare = Error.prepareStackTrace
			var orgCount = Error.stackTraceLimit

			Error.prepareStackTrace = callerFormat
			Error.stackTraceLimit = limit || 1

			var err = new Error
			Error.captureStackTrace(err, func || callee)
			var s = err.stack

			Error.stackTraceLimit = orgCount
			Error.prepareStackTrace = orgPrepare

			return s
		}
	}
})
define('pico/json',function(exports,require,module,define,inherit,pico){
	return {
		parse:function(pjson,deep){
			return JSON.parse(pjson[0], function(k, v){
				switch(k[0]){
				case '$': if(deep)return JSON.parse(pjson[v])
				case '_': return pjson[v]
				default: return v
				}
			})
		},
		stringify:function(json, deep){
			var pjson=[]
			pjson.unshift(JSON.stringify(json, function(k, v){
				switch(k[0]){
				case '$': if(deep)return pjson.push(JSON.stringify(v))
				case '_': return pjson.push(v)
				default: return v
				}
			}))
			return pjson
		},
		path: function(json){
			var current = json

			function unwrap(arr, i) {
				return i < 0 ? (arr.length || 0) + i : i
			}

			function search(key, obj) {
				if (!key || !obj || 'object' !== typeof obj) return
				if (obj[key]) return obj[key]

				var ret = []
				var found
				var ks = Object.keys(obj)
				for(var i=0,k; (k=ks[i]); i++){
					found = search(key, obj[k])
					found && (Array.isArray(found) ? ret.push.apply(ret,found) : ret.push(found))
				}
				return ret.length ? ret : void 0
			}

			function jwalk(){
				if (!arguments.length) return current
				var isArr = Array.isArray(current)

				switch(typeof arguments[0]){
				case 'string':
					var str = arguments[0]

					switch(str){
					default:
						if (isArr){
							if (!current[0][str]) break
							current = current.map( function(o) {
								return o[str]
							} )
						}else{
							if (!current[str]) break
							current = current[str]
						}
						break
					case '..':
						current = search(arguments[1], current) || current
						break
					case '*':
						if (isArr) break
						current = Object.keys(current).map( function(k) {
							return current[k]
						} )
						break
					}
					break
				case 'object':
					var arr = arguments[0]
					if (!Array.isArray(arr)) break
					current = arr.map( function(i) {
						return current[unwrap(current, i)]
					} )
					break
				case 'number':
					var start = unwrap(current, arguments[0])
					var end = unwrap(current, arguments[1]) || current.length-1 || 0
					var interval = arguments[2] || 1
					var next = []
					var a = []
					for (var i=start; i <= end; i+=interval){
						next.push(current[i])
						a.push(i)
					}
					current = next
					break
				case 'function':
					var cb = arguments[0]
					current = isArr ? current.map( cb ) : cb(current)
					break
				}
				Array.isArray(current) && (current = current.filter( function(o) {
					return null != o
				} ))
				if (1 === current.length) current = current.pop()
				return jwalk
			}
			return jwalk
		}
	}
})
define('pico/obj',function(){
	var allows = ['object','function']
	var specialFunc = ['constructor']
	return  {
		extend: function extend(to, from, options){
			var tf=allows.indexOf(typeof to)
			var ft=allows.indexOf(typeof from)
			if (1 === tf) tf = allows.indexOf(typeof to.__proto__)
			if (1 === ft) ft = allows.indexOf(typeof from.__proto__)
			if (!to || null === from || (-1 === ft && ft === tf)) return void 0 === from ? to : from
			if (1===ft) {
				if(ft === tf)from.prototype=to
				return from
			}
			options=options||{}
			var tidy = options.tidy, key, value
			if (Array.isArray(from)){
				if (options.mergeArr){
					to = to || []
					// TODO: change unique to Set when is more commonly support on mobile
					var i, l, unique={}
					for (i=0,l=to.length; i<l; i++){
						if (void 0 === (value = to[i]) && tidy) continue
						unique[value] = value
					}
					for (i=0,l=from.length; i<l; i++){
						if (void 0 === (value = from[i]) && tidy) continue
						unique[value] = value
					}
					to = []
					for (key in unique) to.push(unique[key])
				}else{
					to = from
				}
			}else{
				to = to || {}
				for (key in from){
					value = from[key]
					if (~specialFunc.indexOf(key) || (void 0 === value && tidy)) continue
					to[key] = extend(to[key], value, options)
				}
			}
			return to
		},
		extends: function(to, list, options){
			var e = this.extend
			for(var i=0,f; (f=list[i]); i++){
				to= e(to, f, options)
			}
			return to
		},
		parseInts: function(arr, radix){
			for(var i=0,l=arr.length; i<l; i++){
				arr[i] = parseInt(arr[i], radix)
			}
			return arr
		},
		// pluck([{k:1},{k:2}], 'k') = [1,2]
		pluck: function(objs, key){
			var arr = []
			if (objs.length){
				var map = {}, obj, id, i, l, k
				for(i=0,l=objs.length; i<l; i++){
					obj = objs[i]
					if (!obj) continue
					id = obj[key]
					if (void 0 === id) continue
					map[id] = id
				}
				for(k in map){
					arr.push(map[k])
				}
			}
			return arr
		},
		dotchain: function callee(obj, p, value){
			if (!p || !p.length) return obj
			var o = obj[p.shift()]
			if (o) return callee(o, p)
			return value
		}
	}
})
define('pico/str', function(){
	var Random=Math.random
	function partial(func){
		return function(d){
			return func(pico, d)
		}
	}
	function compileRestUnit(unit){
		var idx=unit.search('[#:%]')
		switch(idx){
		case -1:
		case 0: return unit
		}
		return [unit.substring(0,idx),unit.substr(idx)]
	}
	function compileRestPath(path,idx,output,cb){
		var nidx=path.indexOf('/',idx)
		if (-1===nidx){
			output.push(compileRestUnit(path.substring(idx)))
			return cb(null, output)
		}
		output.push(compileRestUnit(path.substring(idx,nidx)))
		compileRestPath(path,nidx+1,output,cb)
	}
	function compileRestOptional(optionals,output,cb){
		if (!optionals.length) return cb(null,output)
		compileRestPath(optionals.shift(),0,[],function(err,code){
			if (err) return cb(err)
			output.push(code)
			compileRestOptional(optionals,output,cb)
		})
	}
	function parseRestCode(code,unit,units,i,params){
		switch(code[0]){
		default: return code===unit
		case '%': params[code.substr(1)]=parseFloat(unit); break
		case ':': params[code.substr(1)]=unit; break
		case '#': params[code.substr(1)]=units.slice(i).join('/'); break
		}
		return true
	}
	function matchRestCode(units,codes,params){
		if (units.length < codes.length) return false
		for(var i=0,u,c,l=codes.length; i<l; i++){
			c=codes[i]
			u=units[i]
			if (Array.isArray(c)){
				if (0!==u.indexOf(c[0])) return false
				if (!parseRestCode(c[1],u.substr(c[0].length),units,i,params)) return false
			}else{
				if (!parseRestCode(c,u,units,i,params)) return false
			}
		}
		units.splice(0,l)
		return true
	}
	function buildRest(url, tokens, index, params, prefix, mandatory){
		if (tokens.length <= index) return url
		var token = tokens[index++]
		if (!token.charAt) return buildRest(buildRest(url + prefix, token, 0, params, '', mandatory), tokens, index, params, prefix, mandatory)

		if (token.length > 1){
			switch(token.charAt(0)){
			case '%':
			case ':':
			case '#':
				token = params[token.slice(1)]
				if (!token) return mandatory ? '' : url
				break
			}
		}
		url += prefix + token
		return buildRest(url, tokens, index, params, prefix, mandatory)
	}

	return {
		codec: function(num, str){
			for(var i=0,ret='',c; (c=str.charCodeAt(i)); i++){
				ret += String.fromCharCode(c ^ num)
			}
			return ret
		},
		hash: function(str){
			for (var i=0,h=0,c; (c=str.charCodeAt(i)); i++) {
				// same as h = ((h<<5)-h)+c;  h = h | 0 or h = h & h <= Convert to 32bit integer
				h = (h<<3)-h+c | 0
			}
			return h
		},
		rand: function(){
			return Random().toString(36).substr(2)
		},
		pad:function(val,n,str){
			return this.tab(val,n,str)+val
		},
		tab:function(val,n,str){
			var c=n-String(val).length+1
			return Array(c>0?c:0).join(str||'0')
		},
		// src:https://raw.githubusercontent.com/krasimir/absurd/master/lib/processors/html/helpers/TemplateEngine.js
		template:function(html){
			var re = /<%(.+?)%>/g,
				reExp = /(^( )?(var|if|for|else|switch|case|break|{|}|;))(.*)?/g,
				code = 'var r=[];\n',
				cursor = 0,
				match
			var add = function(line, js) {
				js ? (code += line.match(reExp) ? line + '\n' : 'r.push(' + line + ');\n') :
					(code += line !== '' ? 'r.push("' + line.replace(/"/g, '\\"') + '");\n' : '')
				return add
			}
			while((match = re.exec(html))) {
				add(html.slice(cursor, match.index))(match[1], true)
				cursor = match.index + match[0].length
			}
			add(html.substr(cursor, html.length - cursor))
			return partial(new Function('pico', 'd', (code + 'return r.join("");').replace(/[\r\t\n]/g, ' ')))
		},
		// precedence | / # : %
		compileRest:function(rest, output){
			output=output||[]
			if (-1 === rest.search('[|#:%]')) return output
			compileRestOptional(rest.split('|'),[rest],function(err,codes){
				if (err) throw err
				output.push(codes)
			})
			return output
		},
		execRest:function(api,build,params){
			var units=api.split('/')
			for(var i=0,route,j,opt; (route=build[i]); i++){
				if (matchRestCode(units, route[1], params)){
					for(j=2; (opt=route[j]); j++){
						if (!matchRestCode(units, opt, params)) break
					}
					return route[0]
				}
			}
			return null
		},
		buildRest:function(api,build,params,relativePath){
			var codes
			for (var i=0, b; (b = build[i]); i++){
				if (api === b[0]){
					codes = b
					break
				}
			}
			if (!codes) return api
			var url = buildRest('', codes[1], 0, params, '/', true)
			if (!url) return false
			var c
			for (i=2; (c = codes[i]); i++){
				url = buildRest(url, c, 0, params, '/')
			}
			// remove the first slash
			if (relativePath || 1 === url.indexOf('http')) url = url.slice(1)
			return ~url.search('[#%]') ? false : url
		}
	}
})
define('pico/time',function(){
	var
		Max=Math.max,
		Min=Math.min,
		Floor=Math.floor,
		Ceil=Math.ceil,
		SEC = 1000,
		MIN = 60*SEC,
		SAFE_MIN = 90*SEC,
		HR = 60*MIN,
		DAY= 24*HR,
		daynum=function(end,start){
			return (end-start) / DAY
		},
		weeknum=function(date, us, yearoff){
			var
				offset=us?1:0,
				jan1= new Date(date.getFullYear()+(yearoff||0), 0, 1),
				day1=((7-jan1.getDay())%7 + offset),
				days=daynum(date, jan1)

			if (days > day1) return Ceil((days - day1)/7)
			return weeknum(date, us, -1)
		},
		parseQuark=function(quark, min, max){
			var
				q=quark.split('/'),
				q0=q[0]

			if ('*'===q0){
				q[0]=min
			}else{
				q0 = parseInt(q0)
				q0 = Max(min, q0)
				q0 = Min(max, q0)
				q[0] = q0
			}

			if (1===q.length) q.push(0) // interval=1
			else q[1]=parseInt(q[1])

			return q
		},
		parseAtom=function(atom, min, max){
			if ('*'===atom) return 0
			var
				ret=[],
				list=atom.split(',')
			for(var i=0,l,j,r,r0,r1,rm,ri; (l=list[i]); i++){
				r=l.split('-')
				r0=parseQuark(r[0],min,max)
				if (1===r.length){
					ri=r0[1]
					if (ri) for(j=r0[0]; j<=max; j+=ri) ret.push(j)
					else ret.push(r0[0])
					continue
				}
				r1=parseQuark(r[1],min,max)
				j=r0[0]
				rm=r1[0]
				ri=r1[1]||1

				if (j>rm){
					// wrap around
					for(; j>=rm; j-=ri) {
						ret.push(j)
					}
				}else{
					for(; j<=rm; j+=ri) {
						ret.push(j)
					}
				}
			}
			ret.sort(function(a,b){
				return a-b
			})
			return ret
		},
		closest=function(now, list, max){
			if (!list) return now
			if (Max.apply(Math, list.concat(now))===now) return now+(max-now)+Min.apply(Math, list)
			for(var i=0,l=list.length; i<l; i++){
				if (list[i]>=now) return list[i]
			}
			console.error('not suppose to be here',now, list, max)
		},
		nearest=function(now, count, mins, hrs, doms, mons, dows, yrs, cb){
			if (count++ > 3) return cb(0)

			var
				min=closest(now.getMinutes(), mins, 60),
				hr=closest(now.getHours()+Floor(min/60), hrs, 24),
				dom=now.getDate(),
				mon=now.getMonth(),
				yr=now.getFullYear(),
				days=(new Date(yr, mon, 0)).getDate()

			if (dows){
				// if dow set ignore dom fields
				var
					day=now.getDay()+Floor(hr/24),
					dow=closest(day, dows, 7)
				dom+=(dow-day)
			}else{
				dom=closest(dom+Floor(hr/24), doms, days)
			}
			mon=closest(mon+1+Floor(dom/days), mons, 12)

			if (now.getMonth()+1 !== mon) return nearest(new Date(yr, mon-1), count, mins, hrs, doms, mons, dows, yrs, cb)

			yr=closest(yr+Floor((mon-1)/12), yrs, 0)
			if (now.getFullYear() !== yr) return nearest(new Date(yr, mon-1), count, mins, hrs, doms, mons, dows, yrs, cb)

			var then=(new Date(yr, (mon-1)%12)).getTime()
			then+=(dom%days-1)*DAY // beginning of day
			then+=(hr%24)*HR
			then+=(min%60)*MIN

			return cb(then)
		}

	return {
		// fmt: min hr dom M dow yr
		parse: function(fmt){
			var atoms=fmt.split(' ')
			if (atoms.length < 6) return 0
			var mins=parseAtom(atoms[0], 0, 59)
			if (null == mins) return 0
			var hrs=parseAtom(atoms[1], 0, 23)
			if (null == hrs) return 0
			var doms=parseAtom(atoms[2], 1, 31)
			if (null == doms) return 0
			var mons=parseAtom(atoms[3], 1, 12)
			if (null == mons) return 0
			var dows=parseAtom(atoms[4], 0, 6)
			if (null == dows) return 0
			var yrs=parseAtom(atoms[5], 1975, 2075)
			if (null == yrs) return 0

			return [mins, hrs, doms, mons, dows, yrs]
		},
		nearest:function(mins, hrs, doms, mons, dows, yrs, now){
			now = now || Date.now()
			return nearest(new Date(now + SAFE_MIN), 0, mins, hrs, doms, mons, dows, yrs, function(then){
				return then
			})
		},
		daynum:daynum,
		weeknum:weeknum,
		// node.js should compile with
		// ./configure --with-intl=full-icu --download=all
		// ./configure --with-intl=small-icu --download=all
		day: function(date, locale){
			var
				now=new Date,
				mid=new Date(now.getFullYear(),now.getMonth(),now.getDate(),12,0,0),
				diff=mid-date,
				DAY15=DAY*1.5
			if ((diff >= 0 && diff <= DAY15) || (diff <= 0 && diff > -DAY15)){
				if (now.getDate()===date.getDate())return'Today'
				if (now > date) return 'Yesterday'
				return 'Tomorrow'
			}

			locale=locale||'en-US'
			if (now.getFullYear()===date.getFullYear() && weeknum(now)===weeknum(date)) return date.toLocaleDateString(locale, {weekday:'long'})
			return date.toLocaleDateString(locale,{weekday: 'short', month: 'short', day: 'numeric'})
		}
	}
})
define('pico/web',function(exports,require,module,define,inherit,pico){
	var
		PJSON=require('pico/json'),
		Abs = Math.abs,Floor=Math.floor,Random=Math.random,
		API_ACK = 'ack',
		PT_HEAD = 1,
		PT_BODY = 2,
		isOnline = true,
		stdCB = function(err){
			if (err) console.error(err)
		},
		appendFD = function(fd, name, value){
			fd.append(name, value)
		},
		appendObj = function(obj, name, value){
			obj[name] = value
		},
		timeSync = function(net, cb){
			cb = cb || stdCB
			pico.ajax('get', net.url, null, null, function(err, readyState, response){
				if (4 !== readyState) return
				if (err) return cb(err)
				var st = parseInt(response)
				if (isNaN(st)) return cb('invalid timesync response')
				net.serverTime = st
				net.serverTimeAtClient = Date.now()
				cb()
			})
		},
		onResponse = function(err, readyState, response, net){
			if (err && 4===readyState) timeSync(net) // sync time, in case it was due to time error

			// schedule next update
			switch(readyState){
			case 2: // send() and header received
				net.head = null
				net.currPT = PT_HEAD
				net.resEndPos = 0
				break
			case 3: break // body loading 
			case 4: // body received
				break
			}

			if (!response) return

			var
				startPos = net.resEndPos, endPos = -1,
				sep = net.delimiter,
				sepLen = sep.length,
				body = net.body,
				head

			try{
				while(true){
					endPos = response.indexOf(sep, startPos)
					if (-1 === endPos) break

					switch(net.currPT){
					case PT_HEAD:
						net.head = JSON.parse(response.substring(startPos, endPos))
						body.length = 0
						net.currPT = PT_BODY
						break
					case PT_BODY:
						body.push(response.substring(startPos, endPos))
						break
					}
					head = net.head
					if (head && head.len === body.length){
						net.currPT = PT_HEAD

						if (head.resId){
							net.request(API_ACK, {resId:head.resId})
						}
						if (!head.reqId) {
							console.error('incomplete response header: '+JSON.stringify(head))
							return
						}
						if (net.cullAge && net.cullAge < Abs(net.getServerTime()-head.date)) {
							console.error('invalid server time: '+JSON.stringify(head)+' '+Abs(net.getServerTime()-head.date))
							return
						}
						if (net.secretKey && body.length){
							var hmac = CryptoJS.algo.HMAC.create(CryptoJS.algo.MD5, net.secretKey+head.date)

							//key: CryptoJS.HmacMD5(JSON.stringify(data), this.secretKey+t).toString(CryptoJS.enc.Base64),
							for(var i=0,l=body.length; i<l; i++){
								hmac.update(body[i])
							}

							if (head.key !== hmac.finalize().toString(CryptoJS.enc.Base64)){
								console.error('invalid server key: '+JSON.stringify(head))
								return
							}
						}
						if (head.len) head.data = PJSON.parse(body,true)
						net.inbox.push(head)
						net.head = null
					}

					startPos = endPos + sepLen
				}
			}catch(exp){
				// something is wrong
				console.error(exp)
			}
			//readyState 2 may not arrived
			net.resEndPos = 4===readyState?0:startPos
		},
		formation = function(dst, form, cred, prefix_form, prefix_cred){
			prefix_form = prefix_form || ''
			prefix_cred = prefix_cred || ''

			var
				append = dst instanceof FormData ? appendFD : appendObj,
				uri = form.baseURI,
				fieldType, f, fl

			for (var i=0,elements = form.elements,field; (field = elements[i]); i++) {
				if (!field.hasAttribute('name')) continue
				fieldType = field.hasAttribute('type') ? field.getAttribute('type').toUpperCase() : 'TEXT'
				if (fieldType === 'FILE') {
					for (f = 0, fl=field.files.length; f<fl; append(dst, prefix_form+field.name, field.files[f++]));
				} else if ((fieldType !== 'RADIO' && fieldType !== 'CHECKBOX') || field.checked) {
					append(dst, prefix_form+field.name, field.value)
				}//TODO: implement checkbox and radio
			}
			if (cred) for (var k in cred) {
				append(dst, prefix_cred+k, cred[k])
			}

			uri = uri.substring(0, uri.lastIndexOf('/')+1)

			return form.action.substr(uri.length)
		},
		netConfig = function(net, cfg){
			net.url = cfg.url || net.url
			net.secretKey = cfg.secretKey || net.secretKey
			net.cullAge = cfg.cullAge || net.cullAge
			net.delimiter = cfg.delimiter ? JSON.stringify(cfg.delimiter) : net.delimiter
		},
		netReset = function(net){
			net.resEndPos = net.outbox.length = net.acks.length = 0
			net.currPT = PT_HEAD
		}


	function Net(cfg){
		if (!cfg.url) return console.error('url is not set')
		netConfig(this, Object.assign({cullAge:0, delimiter:['&']}, cfg))
		this.reqId = 1 + Floor(Random() * 1000)
		this.inbox = []
		this.outbox = []
		this.uploads = []
		this.callbacks = {}
		this.acks = []
		this.reqs = []
		this.resEndPos = 0
		this.head = null,
		this.body = [],
		this.currPT = PT_HEAD,
		this.serverTime = 0
		this.serverTimeAtClient = 0
	}

	Net.prototype = {
		beat: function(){
			if (this.inbox.length){
				var
					inbox = this.inbox,
					callbacks = this.callbacks,
					reqId, cb

				for(var res; (res=inbox.pop());){
					reqId = res.reqId
					cb = callbacks[reqId]
					if (cb){
						delete callbacks[reqId]
						cb(res.error, res.data)
					}
				}
			}

			// post update tasks, buffer data in memory network if offline
			if (isOnline && (this.uploads.length || this.outbox.length || this.acks.length)){
				var uploads=this.uploads,outbox=this.outbox,acks=this.acks

				if (uploads.length){
					pico.ajax('post', this.url, uploads.shift(), null, onResponse, this)
				}else{
					var reqs = this.reqs = acks.concat(outbox)
					acks.length = outbox.length = 0

					pico.ajax('post', this.url, reqs.join(this.delimiter)+this.delimiter, null, onResponse, this)
				}
			}
		},
		reconnect: function(cfg, cb){
			netConfig(this, cfg)
			netReset(this)
			timeSync(this, function(err){
				cb(err, this)
			})
		},
		submit: function(form, cred, cb){
			if ('undefined'===typeof window || !form || !(form instanceof HTMLFormElement)) return console.error('No HTMLFormElement submitted')

			var reqId = 0

			if (cb){
				reqId = this.reqId++
				this.callbacks[reqId] = cb
			}

			var fd = new FormData()

			fd.append('api', formation(fd, form, cred, 'data/', 'cred/'))
			fd.append('reqId', reqId)

			this.uploads.push(fd)
		},
		// data: optional, usually api specific data
		// cred: optional, usually common data for every api such as credential or session info
		// cb: optional, without cb, reqId will be 0
		request: function(api, data, cred, cb){
			switch(arguments.length){
			case 2:
				if (data instanceof Function){
					cb = data
					data = cred = void 0
				}
				break
			case 3:
				if (cred instanceof Function){
					cb = cred
					cred = void 0
				}
				break
			case 4: break
			default: return console.error('wrong request params!')
			}
			if ('undefined'!==typeof window && data instanceof HTMLFormElement){
				var obj = {}
				api = formation(obj, data)
				data = obj
			}
			if (!api) return console.error('Missing api,  data['+JSON.stringify(data)+']')

			var queue = this.acks
			if (api !== API_ACK){
				queue = this.outbox
				if (queue.length){
					var lastReq = queue.shift()
					if (-1 === lastReq.indexOf(api)){
						queue.unshift(lastReq)
					}
				}
			}

			var reqId = 0
			if (cb){
				reqId = this.reqId++
				this.callbacks[reqId] = cb
			}

			var dataList=data?PJSON.stringify(data,true):[]

			dataList.unshift(JSON.stringify(cred))

			if (dataList.length && this.secretKey){
				var
					t = this.getServerTime(),
					hmac = CryptoJS.algo.HMAC.create(CryptoJS.algo.MD5, this.secretKey+t) // result of utf8 is diff from node.crypto

				//key: CryptoJS.HmacMD5(JSON.stringify(data), this.secretKey+t).toString(CryptoJS.enc.Base64),
				for(var i=0,l=dataList.length; i<l; i++){
					hmac.update(dataList[i])
				}

				dataList.unshift(JSON.stringify({
					api: api,
					reqId: reqId,
					len:dataList.length,
					date: t,
					key: hmac.finalize().toString(CryptoJS.enc.Base64)
				}))
			}else{
				dataList.unshift(JSON.stringify({
					api: api,
					reqId: reqId,
					len:dataList.length
				}))
			}
			queue.push(dataList.join(this.delimiter))
		},
		getServerTime: function(){
			return this.serverTime + (Date.now() - this.serverTimeAtClient)
		},
		test: function(cb){
			timeSync(this, cb)
		}
	}

	return {
		create: function(cfg, cb){
			var net= new Net(cfg)
			timeSync(net, function(err){
				cb && cb(err, net)
			})
			return net
		},
		//window.addEventListener('online', online)
		online: function(){
			isOnline=true
		},
		//window.addEventListener('offline', offlie)
		offline: function(){
			isOnline=false
		}
	}
})
}).apply(null, 'object' === typeof module ? [module, 'exports', require] : [window, 'pico'])