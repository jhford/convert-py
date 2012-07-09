import sys
import os
import subprocess as sp
import tempfile
from multiprocessing import Pool

class EncodingFailure(Exception): pass

def flac_to_mp3(infile, settings=["-V0"], lame_bin='lame',
                metaflac_bin='metaflac', flac_bin='flac', eyeD3_bin='eyeD3'):
    important_tags = ('title', 'artist', 'album', 'tracknumber', 'discnumber')
    # Figure out the metadata.
    data = {}
    print 'BEGIN METADATA "%s"' % os.path.basename(infile)
    for i in important_tags:
        output = unicode(sp.check_output([metaflac_bin, '--no-utf8-convert', '--show-tag=%s' % i,
                                          infile]), encoding='utf-8')
        if '=' in output:
            data[i] = output[output.index('=')+1:].strip()
        else:
            data[i] = output.strip()

    # This exception handler is ugly but I don't know a good
    # way to check if a flac file has a picture without lots
    # of code.  Laziness abounds
    try:
        # Assuming jpg file is really lame
        tmppicfd, tmppicfile = tempfile.mkstemp(prefix='flacpic_', suffix='.jpg')
        os.close(tmppicfd)
        os.unlink(tmppicfile)
        sp.check_call([metaflac_bin,
                       '--export-picture-to=%s'%tmppicfile,
                       infile])
        picture = tmppicfile
    except sp.CalledProcessError:
        picture = None
    print 'END METADATA "%s"' % os.path.basename(infile)

    # Decode flac file to temporary wav file
    tmpfd, tmpfile = tempfile.mkstemp(prefix='flacinput_', suffix='.wav')
    os.close(tmpfd)
    os.unlink(tmpfile)
    print 'BEGIN DECODE "%s"' % os.path.basename(infile)
    sp.check_call([flac_bin, '--silent', '--decode', infile, '--output-name=%s'%tmpfile])
    print 'END DECODE "%s"' % os.path.basename(infile)

    # Encode wav into mp3
    output_file = os.path.join(u'out', data['artist'], data['album'],
                u'%s %s.mp3' % (data['tracknumber'], data['title']))
    try:
        os.makedirs(os.path.dirname(output_file))
    except OSError:
        pass # TODO: do something smarter here
    print 'BEGIN ENCODE "%s"' % os.path.basename(infile)
    sp.check_call([lame_bin, '--quiet'] + settings + [tmpfile, output_file])
    print 'END ENCODE "%s"' % os.path.basename(infile)

    # Set ID3 tags
    print 'BEGIN ID3 "%s"' % os.path.basename(infile)
    devnull = os.open(os.devnull, os.O_WRONLY)
    sp.check_call([eyeD3_bin, u'--to-v2.4',
                   u'--artist=%s' % data['artist'],
                   u'--album=%s' % data['album'],
                   u'--title=%s' % data['title'],
                   u'--track=%s' % data['tracknumber'],
                   u'--set-encoding=utf8',
                   output_file],
                   stdout=devnull,
                   stderr=sp.STDOUT)
    if picture:
        sp.check_call([eyeD3_bin, u'--add-image=%s:FRONT_COVER' % picture,
                       output_file],
                       stdout=devnull,
                       stderr=sp.STDOUT)
    os.close(devnull)
    print 'END ID3 "%s"' % os.path.basename(infile)
    os.unlink(tmpfile)
    if picture:
        os.unlink(tmppicfile)

def main():
    flacs=[]
    for i in sys.argv[1:]:
        with open(i) as f:
            flacs.extend([x.strip() for x in f.readlines()])

    with open('failed', 'a') as failed_files:
        for flac in flacs:
            try:
                flac_to_mp3(flac)
            except sp.CalledProcessError:
                print >> sys.stderr, "WARNING: FAILED TO CONVERT '%s'!!!" % flac
                print >> failed_files, flac

if __name__ == "__main__":
    flacs=[]
    for i in sys.argv[1:]:
        with open(i) as f:
            flacs.extend([x.strip() for x in f.readlines()])

    pool = Pool()
    pool.map_async(flac_to_mp3, flacs)
    main()
