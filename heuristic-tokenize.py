

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
        possible_headers = re.findall('    ([A-Z][^:]+:)', '     '+segment)
        assert len(possible_headers) < 2
        headers = []
        for h in possible_headers:
            if is_title(h.strip(':')):
                headers.append(h)

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


    ### Separate enumerated lists ###
    for segment in segments:
        if '1.' not in segment: 
            new_segments.append(segment)
            continue

        #print '------------START------------'
        #print segment
        #print '-------------END-------------'
        #print

        # generalizes in case the list STARTS this section
        segment = '\n'+segment

        # determine whether this segment contains a bulleted list
        n = 0
        while '\n%d.'%(n+1) in segment:
            n += 1

        # no bulleted list
        if n < 1:
            new_segments.append(segment)
            continue

        print '------------START------------'
        print segment
        print '-------------END-------------'

        print n
        print 

        # break each list into its own line
        for i in range(1,n+1):
            print i
        print 

    exit()

    return text.split('\n')



def strip(s):
    return s.strip()



stopwords = set(['of', 'on', 'or'])
def is_title(text):
    # Are all non-stopwords capitalized?
    for word in text.split():
        if word in stopwords: continue
        if not word[0].isupper():
            return False

    # optionally: could assert that it is less than 6 tokens

    return True


if __name__ == '__main__':
    main()


