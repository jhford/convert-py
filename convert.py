#!/usr/bin/env python
import os
import sys
import subprocess as sp
import tempfile
import imghdr
import logging

# I don't want to have to run with PYTHONPATH
sys.path.append(os.path.abspath(os.path.split(__file__.rstrip(os.sep))[0]))
import util
import mp

class EncodingFailure(Exception): pass

def flac_to_mp3(infile, settings=["-V0"], lame_bin='lame',
                metaflac_bin='metaflac', flac_bin='flac', eyeD3_bin='eyeD3'):
    log = logging.getLogger(__name__)
    important_tags = ('title', 'artist', 'album', 'tracknumber', 'discnumber')
    # Figure out the metadata.
    data = {}
    log.info('BEGIN METADATA "%s"', os.path.basename(infile))
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
        raise Exception() # TEMPORARY
        # Assuming jpg file is really lame
        tmppicfd, tmppicfile = tempfile.mkstemp(prefix='flacpic_', suffix='.jpg')
        os.close(tmppicfd)
        os.unlink(tmppicfile)
        sp.check_output([metaflac_bin,
                       '--export-picture-to=%s'%tmppicfile,
                       infile])
        picture = tmppicfile
    except sp.CalledProcessError:
        log.debug('could not extract picture from infile')
        picture = None
    except Exception:
        picture=None # XXX THIS IS TEMPORARY!!!
    log.info('END METADATA "%s"', os.path.basename(infile))

    # Decode flac file to temporary wav file
    tmpfd, tmpfile = tempfile.mkstemp(prefix='flacinput_', suffix='.wav')
    os.close(tmpfd)
    os.unlink(tmpfile)
    log.info('BEGIN DECODE "%s"', os.path.basename(infile))
    sp.check_call([flac_bin, '--silent', '--decode', infile, '--output-name=%s'%tmpfile])
    log.info('END DECODE "%s"', os.path.basename(infile))

    # Encode wav into mp3
    output_file = os.path.join(u'out', data['artist'], data['album'],
                u'%s %s.mp3' % (data['tracknumber'], data['title']))
    try:
        os.makedirs(os.path.dirname(output_file))
    except OSError:
        pass # TODO: do something smarter here
    log.info('BEGIN ENCODE "%s"', os.path.basename(infile))
    sp.check_call([lame_bin, '--quiet'] + settings + [tmpfile, output_file])
    log.info('END ENCODE "%s"', os.path.basename(infile))

    # Set ID3 tags
    log.info('BEGIN ID3 "%s"', os.path.basename(infile))
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
    log.info('END ID3 "%s"', os.path.basename(infile))
    os.unlink(tmpfile)
    if picture:
        os.unlink(tmppicfile)
    return 0

def main():
    log = util.setup_logging(__name__, volume=0)
    log.info("Converting some files for you")

    flacs=[]
    for i in sys.argv[1:]:
        with open(i) as f:
            flacs.extend([x.strip() for x in f.readlines()])
    jobs = []
    for flac in flacs:
        jobs.append(mp.PyFuncJob(flac_to_mp3, flac))
    mp.ThreadPool(jobs).run_jobs()


if __name__ == "__main__":
    main()
