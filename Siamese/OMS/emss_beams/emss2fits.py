#!/usr/bin/python
# -*- coding: utf-8 -*-

if __name__ == "__main__":

  # setup some standard command-line option parsing
  #
  import sys
  import numpy
  import math
  DEG = math.pi/180;
  from optparse import OptionParser,OptionGroup

  
  parser = OptionParser(usage="""%prog: [options] <*.pat file(s)> <FITS file>""",
      description=
"""Converts EMSS ASCII beam patterns to FITS files. Multiple frequency patterns may be given.
For a compound pattern built from a  sum of components (i.e. feed, main reflector, subreflector), 
separate the per-component groups with '+'.""");

  parser.add_option("-x",action="store_true",
                    help="generate the X component (default)");
  parser.add_option("-y",action="store_true",
                    help="generate the Y beam component");
  parser.add_option("--ampl",action="store_true",
                    help="generate the amplitude pattern.");
  parser.add_option("--real",action="store_true",
                    help="generate the real pattern.");
  parser.add_option("--imag",action="store_true",
                    help="generate the imaginary pattern. Default generates all three.");
  parser.add_option("-i","--interpolator",choices=("ps","grid"),default="grid",
                    help="select interpolation algorithm: 'ps' (polar spline), 'grid' (gridder). Default is %default.");
  parser.add_option("-A","--no-ampl-interpol",action="store_true",
                    help="disable amplitude interpolation");
  parser.add_option("-s","--spline-order",type='int',default=3,
                    help="spline order, 1 to 3. Default is %default.");
  parser.add_option("-r","--radius",metavar="PIXELS",type="int",default=512,
                    help="radius of FITS file, in pixels. Resulting NAXISn will be 2*radius+1.");
  parser.add_option("-R","--resolution",metavar="DEG",type="float",default=0.01,
                    help="resolution of FITS file, in degrees. Default is %default.");
  parser.add_option("--scale",type="float",default=1.,
                    help="rescale the beam by the given factor.");
  parser.add_option("-f","--frequency",metavar="MHz",type="float",default=0,
                    help="first frequency plane, MHz.");
  parser.add_option("-n","--num-freq",type="int",default=1,
                    help="number of frequency planes. Default is %default.");
  parser.add_option("-d","--delta-freq",metavar="MHz",type="float",default=1,
                    help="frequency stepping, in MHz. Default is %default.");
  parser.add_option("-v","--verbose",metavar="LEVEL",type="int",default=0,
                    help="verbosity level, higher for more messages.");
  parser.add_option("-T","--timestamps",action="store_true",
                    help="include timestamps with messages.");

  (options,args) = parser.parse_args();
  
  if len(args) < 2:
    parser.error("At least one input *.pat file and one output .fits file must be given");
  
  patfiles = args[:-1];
  fitsfile = args[-1];
  
  # get basename of FITS file, if all three need to be generated
  nout = sum(map(bool,(options.ampl,options.real,options.imag)));
  if nout > 1:
    parser.error("Only one of --ampl/--real/--imag may be specified");
  # if nout=0, generate three FITS files, so take the basename  
  elif nout == 0:
    if fitsfile.upper().endswith('.FITS'):
      fitsfile = os.path.splitext(fitsfile)[0];
  # else just 1 file, make sure it has fits extension
  else:
    if not fitsfile.upper().endswith('.FITS'):
      fitsfile += ".fits";
    
  from EMSSVoltageBeam import _verbosity,EMSSVoltageBeamPS,EMSSVoltageBeamGridder,dprint,dprintf
  _verbosity.set_verbose(options.verbose);
  _verbosity.enable_timestamps(options.timestamps);
  
  # how many compound beams do we have
  dprint(1,"reading pattern files");
  beam_components = [];
  while patfiles:
    try:
      endgroup = patfiles.index('+');
    except:
      endgroup = len(patfiles);
    # make a beam component
    if endgroup:
      if options.interpolator == "ps":
        interpolator = EMSSVoltageBeamPS;
      else:
        interpolator = EMSSVoltageBeamGridder;
      print "Using interpolator %s %s"%(interpolator.__name__,
        "w/o amplitude interpolation" if options.no_ampl_interpol else "with amplitude interpolation");
      vb = interpolator(patfiles[:endgroup],y=options.y,
                        spline_order=options.spline_order,
                        ampl_interpolation=not options.no_ampl_interpol);
      print "Creating %s voltage beam from %s"%("Y" if options.y else "X",
            " ".join(patfiles[:endgroup]));
      beam_components.append(vb);
    del patfiles[:endgroup+1];
  
  if not beam_components:
    parser.error("At least one input *.pat file must be given");
  
  dprint(1,"interpolating beam patterns");

  # if frequency is not specified, pick first one 
  freq0 = options.frequency;
  if options.frequency:
    freq0 = options.frequency*1e+6;
  else:
    freq0 = beam_components[0].freqGrid()[0];
  freq = numpy.arange(options.num_freq)*options.delta_freq*1e+6 + freq0;
  
  if options.interpolator == "ps":
    # create coordinates for interpolation
    # note that the interpolator classes expect direction cosines (i.e. sines w.r.t. sin centre),
    # whereas here we make a regularly-gridded image in degrees
    l0 = numpy.sin(numpy.arange(-options.radius,options.radius+1)*options.resolution*DEG*options.scale);
    l0,m0 = numpy.meshgrid(l0,l0);
    images = [ vb.interpolate(l0,m0,freq=freq,freqaxis=2) for vb in beam_components ];
  elif options.interpolator == "grid":
    l0 = numpy.arange(-options.radius,options.radius+1)*options.resolution*DEG*options.scale;
    images = [ vb.grid(l0,l0,freq) for vb in beam_components ];

  dprint(1,"generating FITS images");
  image = sum(images);
  
  # if freq axis missing, reshape
  if image.ndim < 3:
    image = image.reshape(list(image.shape)+[1]);
  
  # create FITS file
  image = image.transpose();
  
  import pyfits
  import os
  import os.path
  
  npix = options.radius*2 + 1;
  print "Generating FITS images of %dx%d pixels, at a resolution of %g deg/pix"%(npix,npix,options.resolution);
  print "Full image size will be %fx%f deg"%(options.resolution*npix,options.resolution*npix);
  print "Frequency axis: %s MHz"%",".join(map(str,freq*1e-6));
  
  def make_image (filename,data,what):
    hdu = pyfits.PrimaryHDU(data);
    hdr = hdu.header;
    hdr.update('CTYPE1','L',"");
    hdr.update('CRPIX1',options.radius+1,"");
    hdr.update('CRVAL1',0,"");
    hdr.update('CDELT1',options.resolution,"");
    hdr.update('CUNIT1','DEG',"");
    hdr.update('CTYPE2','M',"");
    hdr.update('CRPIX2',options.radius+1,"");
    hdr.update('CRVAL2',0,"");
    hdr.update('CDELT2',options.resolution,"");
    hdr.update('CUNIT2','DEG',"");
    hdr.update('CTYPE3','FREQ',"");
    hdr.update('CRPIX3',1,"");
    hdr.update('CRVAL3',freq0,"");
    hdr.update('CDELT3',options.delta_freq*1e+6,"");
    hdr.update('CUNIT3','HZ',"");
    if os.path.exists(filename):
      os.unlink(filename);
    hdu.writeto(filename,clobber=True);
    print "Wrote %s to %s"%(what,filename);
  
  if not nout or options.ampl:
    make_image(fitsfile if options.ampl else fitsfile+"_ampl.fits",abs(image),"amplitude pattern");
  if not nout or options.real:
    make_image(fitsfile if options.real else fitsfile+"_real.fits",image.real,"real pattern");
  if not nout or options.imag:
    make_image(fitsfile if options.imag else fitsfile+"_imag.fits",image.imag,"imaginary pattern");
  