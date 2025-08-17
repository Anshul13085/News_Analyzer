This is a multilingual news analyzer.
It scrapes data from news sites and displays their headlines, summary, sentiment and bias.
It is powered by elastisearch.
The motive for this is that it will show news from local sites and sources in India which may not be in english so it also has a translate functionality so you can be aware of your local news too.
Currently it is for 1 site only because of defensive bots on varius sites for repeated requests, because of the time constraint there are no local sites but i will do that in the upcoming dates because it will take some time to implement and test if the translator is working or not and if it is giving desired output.
The next thing left to add because of the time constraint is that there will be a different search section where one can paste or write an article and my site will check if it is real or fake because the current social media cannot be fully trusted.
Some functionalities of the project do exist like the summarizer, bias, fact checking, etc. but there is no site to my knowledge that displays all the features of my project alltogether that is why it is unique.
////////////////////////
////////////////////////
How too run the project:
after downloading all the dependencies,
   you run the elasticsearch bat file: .\elastisearch.bat (from the bin location of this file)
   on a different terminal you start the elasticsearch: curl http://localhost:9200
   on a different terminal you start up the whole backend: uvicorn backend.main:app --reload --port 8000
   then on a different terminal you start up the react app: cd frontend
                                                            npm start

remember to run in this order only.
///////////////////////
///////////////////////
