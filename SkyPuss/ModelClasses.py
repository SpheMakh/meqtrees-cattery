import math
import sets

AtomicTypes = dict(bool=bool,int=int,float=float,complex=complex,str=str,list=list,tuple=tuple,dict=dict,NoneType=lambda x:None);

class ModelItem (object):
  """ModelItem is a base class for all model items. ModelItem provides functions
  for saving, loading, and initializing items, using class attributes that describe the 
  item's structure.
  A ModelItem has a number of named attributes (both mandatory and optional), which are 
    sufficient to fully describe the item.
  A ModelItem is constructed by specifying its attribute values. Mandatory attributes are
    passed as opositional arguments to the constructor, while optional attributes are passed
    as keyword arguments.
  'mandatory_attrs' is a class data member that provides a list of mandatory attributes.
  'optional_attrs' is a class data member that provides a dict of optional attributes and their
      default values (i.e. their value when missing). Subclasses are expected to redefine these
      attributes.
  """;
  
  # list of mandatory item attributes
  mandatory_attrs  = [];
  # dict of optional item attributes (key is name, value id default value)
  optional_attrs   = {};
  # True is arbitrary extra attributes are allowed
  allow_extra_attrs = False;
  # dict of rendertags for attributes. Default is to render ModelItems with the "A" tag,
  # and atomic attributes with the "TD" tag
  attr_rendertag   = {};
  # dict of verbosities for attributes. If an entry is present for a given attribute, then 
  # the attribute's text representation will be rendered within its tags
  attr_verbose     = {};
  
  def __init__ (self,*args,**kws):
    """The default ModelItem constructor treats its positional arguments as a list of
    mandatory attributes, and its keyword arguments as optional attributes""";
    # check for argument errors
    if len(args) < len(self.mandatory_attrs):
      raise TypeError,"too few arguments in constructor of "+self.__class__.__name__;
    if len(args) > len(self.mandatory_attrs):
      raise TypeError,"too many arguments in constructor of "+self.__class__.__name__;
    # set mandatory attributes from argument list
    for attr,value in zip(self.mandatory_attrs,args):
      setattr(self,attr,value);
    # set optional attributes from keywords
    for kw,default in self.optional_attrs.iteritems():
      setattr(self,kw,kws.pop(kw,default));
    # set extra attributes, if any are left
    self._extra_attrs = sets.Set();
    if self.allow_extra_attrs:
      for kw,value in kws.iteritems():
        self.setAttribute(kw,value);
    elif kws:
        raise TypeError,"unknown parameters %s in constructor of %s"%(','.join(kws.keys()),self.__class__.__name__);
        
  def registerClass (classobj):
    globals()[classobj.__name__] = classobj;
  registerClass = classmethod(registerClass);
  
  def setAttribute (self,attr,value):
    self._extra_attrs.add(attr);
    setattr(self,attr,value);
    
  def removeAttribute (self,attr):
    if hasattr(self,attr):
      delattr(sel,attr);
    self._extra_attrs.discard(attr);
    
  def getExtraAttributes (self):
    return  [ (attr,getattr(self,attr)) for attr in self._extra_attrs ];
  
  def getAttributes (self):
    """Returns list of non-default attributes""";
    attrs = [ (attr,getattr(self,attr)) for attr in self.mandatory_attrs ];
    for attr,default in self.optional_attrs.iteritems():
      val = getattr(self,attr,default);
      if val != default:
        attrs.append((attr,val));
    attrs += [ (attr,getattr(self,attr)) for attr in self._extra_attrs ];
    return attrs;
    
  def strAttributes (self,sep=",",label=True,
                                   float_format="%.2g",complex_format="%.2g%+.2gj"):
    """Renders attributes as string""";
    fields = [];
    for attr,val in self.getAttributes():
      ss = (label and "%s="%attr) or "";
      if isinstance(val,float):
        ss += float_format%val;
      elif isinstace(val,complex):
        ss += complex_format%val;
      else:
        ss += str(val);
      fields.append(ss);
    return sep.join(fields);
      
  def _resolveTags (self,tags,attr=None):    
    """helper function called from renderMarkup() and renderAttrMarkup() below to
    figure out which HTML tags to enclose a value in. Return value is tuple of (tag,endtag,rem_tags), where
    tag is the HTML tag to use (or None for default, usually "A"), endtag is the closing tag (including <> and whitespace, if any),
    and rem_tags is to be passed to child items' resolveMarkup() """;
    # figure out enclosing tag
    if not tags:
      tag,tags = None,None;  # use default
    elif isinstance(tags,str):
      tag,tags = tags,None;           # one tag supplied, use that here and use defaults for sub-items
    elif isinstance(tags,(list,tuple)):  
      tag,tags = tags[0],tags[1:];   # stack of tags supplied: use first here, pass rest to sub-items
    else:
      raise ValueError,"invalid 'tags' parameter of type "+str(type(tags));
    # if tag is None, use default
    tag = tag or self.attr_rendertag.get(attr,None) or "A";
    if tag.endswith('\n'):
      tag = tag[:-1];
      endtag = "</%s>\n"%tag;
    else:
      endtag = "</%s> "%tag;
    return tag,endtag,tags;
  
  def renderMarkup (self,tags=None,attrname=None):
    """Makes a markup string corresponding to the model item.
    'tags' is the HTML tag to use.
    If 'verbose' is not None, a text representation of the item (using str()) will be included
    as HTML text between the opening and closing tags.
    """;
    tag,endtag,tags = self._resolveTags(tags,attrname);
    # opening tag
    markup = "<%s mdltype=%s "%(tag,type(self).__name__);
    if attrname is not None:
      markup += "mdlattr=\"%s\" "%attrname;
    markup +=">";
    # write mandatory attributes
    for attr in self.mandatory_attrs:
      markup += self.renderAttrMarkup(attr,getattr(self,attr),tags=tags,mandatory=True);
    # write optional attributes only wheh non-default
    for attr,default in self.optional_attrs.iteritems():
      val = getattr(self,attr,default);
      if val != default:
        markup += self.renderAttrMarkup(attr,val,tags=tags);
    # write extra attributes
    for attr in self._extra_attrs:
      markup += self.renderAttrMarkup(attr,getattr(self,attr),tags=tags);
    # closing tag
    markup += endtag;
    return markup;
    
  def renderAttrMarkup (self,attr,value,tags=None,verbose=None,mandatory=False):
    # render ModelItems recursively via renderMarkup() above
    if isinstance(value,ModelItem):
      return value.renderMarkup(tags,attrname=(not mandatory and attr) or None);
    # figure out enclosing tags
    tag,endtag,tags = self._resolveTags(tags,attr);
    # render opening tags
    markup = "<%s mdltype=%s "%(tag,type(value).__name__);
    if not mandatory:
      markup += "mdlattr=\"%s\" "%attr;
    # render lists or tuples iteratively
    if isinstance(value,(list,tuple)):
      markup += ">";
      for i,item in enumerate(value):
        markup += self.renderAttrMarkup(str(i),item,mandatory=True,tags=tags);
    # render dicts iteratively
    elif isinstance(value,dict):
      markup += ">";
      for key,item in value.iteritems():
        markup += self.renderAttrMarkup(key,item,tags=tags);
    # render everything else inline
    else:
      markup += "mdlval=\"%s\">"%repr(value);
      verbose = verbose or (attr and self.attr_verbose.get(attr));
      if verbose:
        markup += ''.join((verbose,str(value)));
      else:
        markup += ':'.join((attr,str(value)));
    markup += endtag;
    return markup;

class Position (ModelItem):
  mandatory_attrs  = [ "ra","dec" ];
  
  def lm_ncp (self,ra0,dec0):
    """Converts position to lm relative to ra0,dec0 (NCP projection)""";
    # this is a temporary kludge:
    return self.ra-ra0,self.dec-dec0;
    
  def lm_sin (self,ra0,dec0):
    """Converts position to lm relative to ra0,dec0 (SIN projection)""";
    return self.ra-ra0,self.dec-dec0;
    
  def ra_hms (self):
    """Returns RA as tuple of (h,m,s)""";
    # convert negative values
    rad = self.ra;
    while rad < 0:
        rad += 2*math.pi;
    rad *= 12.0/math.pi;
    hr = int(rad); 
    rad = (rad-hr)*60;
    mins=int(rad)
    rad = (rad-mins)*60;
    return (hr%24,mins%60,rad);
    
  def dec_dms (self):
    """Returns Dec as tuple of (d,m,s)""";
    rad = self.dec;
    if rad < 0:
        mult = -1;
        rad = abs(rad);
    else:
        mult = 1
    rad *= 180.0/math.pi
    deg = int(rad); 
    rad = (rad-deg)*60;
    mins=int(rad)
    rad = (rad-mins)*60;
    return (mult*(deg%180),mins%60,rad);

class Flux (ModelItem):
  mandatory_attrs  = [ "I" ];
  
class Polarization (Flux):
  mandatory_attrs  = Flux.mandatory_attrs + [ "Q","U","V" ];
  
class PolarizationWithRM (Polarization):
  mandatory_attrs = Polarization.mandatory_attrs + [ "rm","freq0" ];

class Spectrum (ModelItem):
  pass;

class SpectralIndex (Spectrum):
  mandatory_attrs  = [ "spi","freq0" ];
    
class Shape (ModelItem):
  """Abstract base class for a source's brightness distribution"""
  pass;

class Gaussian (Shape):
  typecode = "Gau";
  mandatory_attrs  = [ "ex","ey","pa" ];
  
class FITSImage (Shape):
  typecode = "Img";
  mandatory_attrs  = [ "filename" ];

