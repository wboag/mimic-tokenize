

import sys
import nltk
import re
import os


def main():

    # read text file from command line
    if len(sys.argv) != 2:
        print >>sys.stderr, '\n\tusage: python %s <txt-file>\n' % sys.argv[0]
        exit(1)
    mimic_note_file = sys.argv[1]

    category = os.path.abspath(mimic_note_file).split('/')[-2]

    print
    print mimic_note_file
    print category
    print

    with open(mimic_note_file, 'r') as f:
        text = f.read()

    # tokenize
    sents = sent_tokenize(text, category)




def sent_tokenize(text, category):

    #print nltk.sent_tokenize('number one! the challenge, demand satisfaction. if they apologize no need for further action')
    #print text

    text = text.strip()

    phi_tags = re.findall('(\[\*\*.*?\*\*\])', text)
    for i,tag in enumerate(phi_tags):
        text = text.replace(tag, '__PHI_%d__' % i)
        #text = text.replace(tag, '__PHI__')

    '''
    Thoughts & Strategies
        - If two newlines separate them, then they aren't in the same sentence
        - If you reach a segment that has one token per line, then they are each a sent
        - If something begins with Capitalized Words and a colon, then section header
            - If a line begins with Capitalized word, then probably new sentence
            - If a short line ends with a colon, then it is probably a section header
        - If a newline happens in between matching parens, then ignore newline
        - Identify prose v nonprose. Use nltk.sent_tokenize on prose
            - It's not perfect, but it is pretty good with ignoring mid-sentence newlines
        - section header: "\n------ Protected Section ------\n"
        - how do I get something like: 
            - "Admission Date:    2123-12-25       Discharge Date:    2124-1-14"
            - requires mapping the label & answer
                - could look for any time it is "Noun-Phrase : thing" 
        - Should really try to characterize the KIND of report
            - hopefully report is labeled (e.g. discharge, nursing, radiology)
            - if not, maybe I could train a classifier to predict that category
            - I think that could really help for specialized heuristics
        - If you can detect a bulleted list, then those are sentences
            - sometimes the bullets are hyphens "-", sometimes numbers "1."
        - discharge summaries very much have their own neat format
        - ecg reports are very short & seem to be exclusively prose
        - echo reports are VERY structured. definitely useful to do a echo-specific one
        - nursing notes have a linear structure. sections are easily identifiable
        - nursing_other notes are typically very short (and parse-able)
        - radiology reports have lots of "________________________" sections
            - seems like they always have "MEDICAL CONDITION" and "FINAL REPORT" sections
        - found list example where "1." is its own line and its info is own next line :/
            - could be rehab-specific for notes
        - strong consistency format in social_work
    '''

    if category == 'discharge_summary':
        sents = sent_tokenize_discharge_summary(text)

    for i in range(len(sents)):
        tags = re.findall('(__PHI_(\d+)__)', sents[i])
        for tag,ind in tags:
            sents[i] = sents[i].replace(tag, phi_tags[int(ind)])

    return sents


def word_tokenize(sent):

    '''
    We can't assume the notes are synth-id'd, and we dont want our tokenizer breaking
      [**Doctor First Name**] into a string of tokens, so we should:
        1. at the beginning, findall() all PHI are save their content
        2. replace them with placeholder unqiue single-token __PHI1__ tokens
        3. at the end of the function, replace all of the placeholders with orig values
    '''
    phi_tags = re.findall('(\[\*\*.*?\*\*\])', sent)
    for i,tag in enumerate(phi_tags):
        sent = sent.replace(tag, '__PHI_%d__' % i)
        #text = text.replace(tag, '__PHI__')

    '''
    tags = re.findall('(__PHI_(\d+)__)', sents[i])
    for tag,ind in tags:
        sents[i] = sents[i].replace(tag, phi_tags[int(ind)])
    '''



def sent_tokenize_discharge_summary(text):

    # long sections are OBVIOUSLY different sentences
    text = re.sub('---+', '\n\n---\n\n', text)
    text = re.sub('___+', '\n\n___\n\n', text)
    text = re.sub('\n\n+', '\n\n', text)

    segments = text.split('\n\n')

    # strategy: break down segments and chip away structure until just prose.
    #           once you have prose, use nltk.sent_tokenize()

    ### Separate section headers ###
    new_segments = []

    # deal with this one edge case (multiple headers per line) up front
    m1 = re.match('(Admission Date:) (.*) (Discharge Date:) (.*)', segments[0])
    m2 = re.match('(Date of Birth:) (.*) (Sex:) (.*)'            , segments[1])
    if m1:
        new_segments += list(map(strip,m1.groups()))
        segments = segments[1:]
    if m2:
        new_segments += list(map(strip,m2.groups()))
        segments = segments[1:]

    for segment in segments:
        # find all section headers
        #possible_headers   = re.findall('    ([A-Z][^:]+:)', '    '+segment)
        possible_headers  = re.findall('\n([A-Z][^:]+:)', '\n'+segment)
        #assert len(possible_headers) < 2, str(possible_headers)
        headers = []
        for h in possible_headers:
            if is_title(h.strip().strip(':')):
                headers.append(h.strip())

        # split text into new segments, delimiting on these headers
        for h in headers:
            segment = segment.replace(h, '\n\n'+h+'\n\n')
            segment = re.sub('\n\n+', '\n\n', segment)
            segs = segment.split('\n\n')
            assert len(segs) == 3
            prefix = segs[0]
            rest = segs[2]

            # add the prefix
            if len(prefix) > 0:
                new_segments.append(prefix.strip())

            # add the header
            new_segments.append(h.strip())

            # remove the prefix from processing
            segment = rest.strip()

        # add the final piece (aka what comes after all headers are processed)
        if len(segment) > 0:
            new_segments.append(segment.strip())

    segments = list(new_segments)
    new_segments = []

    '''
    for segment in segments:
        print '------------START------------'
        print segment
        print '-------------END-------------'
        print
    exit()
    '''

    ### Separate enumerated lists ###
    for segment in segments:
        if not re.search('\n\d+\.', '\n'+segment): 
            new_segments.append(segment)
            continue

        #print '------------START------------'
        #print segment
        #print '-------------END-------------'
        #print

        # generalizes in case the list STARTS this section
        segment = '\n'+segment

        # determine whether this segment contains a bulleted list
        start = int(re.search('\n(\d+)\.', '\n'+segment).groups()[0])
        n = start
        while '\n%d.'%n in segment:
            n += 1
        n -= 1

        # no bulleted list
        if n < 1:
            new_segments.append(segment)
            continue

        '''
        print '------------START------------'
        print segment
        print '-------------END-------------'

        print start,n
        print 
        '''

        # break each list into its own line
        # challenge: not clear how to tell when the list ends if more text happens next
        for i in range(start,n+1):
            prefix  = segment[:segment.index('\n%d.'%i)].strip()
            segment = segment[ segment.index('\n%d.'%i):].strip()

            if len(prefix)>0:
                new_segments.append(prefix)

        if len(segment)>0:
            new_segments.append(segment)

    segments = list(new_segments)
    new_segments = []

    '''
        TODO: Big Challenge

        There is so much variation in what makes a list. Intuitively, I can tell it's a
        list because it shows repeated structure (often following a header)

        Examples of some lists (with numbers & symptoms changed around to noise)

            Past Medical History:
            -- Hyperlipidemia
            -- lactose intolerance
            -- Hypertension


            Physical Exam:
            Vitals - T 82.2 BP 123/23 HR 73 R 21 75% on 2L NC
            General - well appearing male, sitting up in chair in NAD
            Neck - supple, JVP elevated to angle of jaw 
            CV - distant heart sounds, RRR, faint __PHI_43__ murmur at


            Labs:
            __PHI_10__ 12:00PM BLOOD WBC-8.8 RBC-8.88* Hgb-88.8* Hct-88.8*
            MCV-88 MCH-88.8 MCHC-88.8 RDW-88.8* Plt Ct-888
            __PHI_14__ 04:54AM BLOOD WBC-8.8 RBC-8.88* Hgb-88.8* Hct-88.8*
            MCV-88 MCH-88.8 MCHC-88.8 RDW-88.8* Plt Ct-888
            __PHI_23__ 03:33AM BLOOD WBC-8.8 RBC-8.88* Hgb-88.8* Hct-88.8*
            MCV-88 MCH-88.8 MCHC-88.8 RDW-88.8* Plt Ct-888
            __PHI_109__ 03:06AM BLOOD WBC-8.8 RBC-8.88* Hgb-88.8* Hct-88.8*
            MCV-88 MCH-88.8 MCHC-88.8 RDW-88.8* Plt Ct-888
            __PHI_1__ 05:09AM BLOOD WBC-8.8 RBC-8.88* Hgb-88.8* Hct-88.8*
            MCV-88 MCH-88.8 MCHC-88.8 RDW-88.8* Plt Ct-888
            __PHI_26__ 04:53AM BLOOD WBC-8.8 RBC-8.88* Hgb-88.8* Hct-88.8*
            MCV-88 MCH-88.8 MCHC-88.8 RDW-88.8* Plt Ct-888
            __PHI_301__ 05:30AM BLOOD WBC-8.8 RBC-8.88* Hgb-88.8* Hct-88.8*
            MCV-88 MCH-88.8 MCHC-88.8 RDW-88.8* Plt Ct-888


            Medications on Admission:
            Allopurinol 100 mg DAILY
            Aspirin 250 mg DAILY
            Atorvastatin 10 mg DAILY
            Glimepiride 1 mg once a week.
            Hexavitamin DAILY
            Lasix 50mg M-W-F; 60mg T-Th-Sat-Sun
            Metoprolol 12.5mg TID
            Prilosec OTC 20 mg once a day
            Verapamil 120 mg SR DAILY
    '''

    ### Remove lines with inline titles from larger segments (clearly nonprose)
    for segment in segments:
        '''
        With: __PHI_6__, MD __PHI_5__
        Building: De __PHI_45__ Building (__PHI_32__ Complex) __PHI_87__
        Campus: WEST
        '''

        lines = segment.split('\n')

        buf = []
        for i in range(len(lines)):
            if is_inline_title(lines[i]):
                if len(buf) > 0:
                    new_segments.append('\n'.join(buf))
                buf = []
            buf.append(lines[i])
        if len(buf) > 0:
            new_segments.append('\n'.join(buf))

    segments = list(new_segments)
    new_segments = []


    # Going to put one-liner answers with their sections 
    # (aka A A' B B' C D D' -->  AA' BB' C DD' )
    N = len(segments)
    for i in range(len(segments)):
        # avoid segfaults
        if i==0: continue

        if     segments[i].count('\n') == 0       and \
               is_title(segments[i-1].strip(':')) and \
           not is_title(segments[i  ].strip(':')):
            if (i == N-1) or is_title(segments[i+1].strip(':')):
                new_segments = new_segments[:-1]
                new_segments.append(segments[i-1] + ' ' + segments[i])
        else:
            new_segments.append(segments[i])

    segments = list(new_segments)
    new_segments = []


    for segment in segments:
        print '------------START------------'
        print segment
        print '-------------END-------------'
        print

    exit()

    return text.split('\n')



def strip(s):
    return s.strip()



def is_inline_title(text):
    m = re.search('^([a-zA-Z ]+): ', text)
    if not m:
        return False

    return is_title(m.groups()[0])



stopwords = set(['of', 'on', 'or'])
def is_title(text):
    # Are all non-stopwords capitalized?
    for word in text.split():
        if word in stopwords: continue
        if not word[0].isupper():
            return False

    # I noticed this is a common issue (non-title aapears at beginning of line)
    if text == 'Disp':
        return False

    # optionally: could assert that it is less than 6 tokens

    return True


if __name__ == '__main__':
    main()


