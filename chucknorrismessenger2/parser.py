import sgmllib

class ChuckNorrisParser(sgmllib.SGMLParser):

    def __init__(self, verbose=0):
        sgmllib.SGMLParser.__init__(self, verbose)
        self.facts = []
        self._process_fact = False

    def parse(self, data):
        self.feed(data)
        self.close()

    def start_a(self, attributes):
        for name, value in attributes:
            if name == 'href' and value.startswith('index.php?pid=fact&person=chuck'):
                self._process_fact = True
            continue

    def handle_data(self, data):
        if self._process_fact:
            # Skip title
            if data.strip() != 'Chuck Norris':
                self.facts.append(str(data))
            self._process_fact = False


