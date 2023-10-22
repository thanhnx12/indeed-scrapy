import re
import json
import scrapy
from urllib.parse import urlencode

class IndeedJobSpider(scrapy.Spider):
    name = "indeed_jobs"
    custom_settings = {
        'FEEDS': { 'data/%(name)s_%(time)s.json': { 'format': 'json',}}
        }

    def get_indeed_search_url(self, keyword, location, offset=0):
        parameters = {"q": keyword, "l": location, "filter": 0, "start": offset}
        return "https://vn.indeed.com/jobs?" + urlencode(parameters)


    def start_requests(self):
        keyword_list = ['software engineer']
        location_list = ['Hà Nội']
        for keyword in keyword_list:
            for location in location_list:
                indeed_jobs_url = self.get_indeed_search_url(keyword, location)
                yield scrapy.Request(url=indeed_jobs_url, callback=self.parse_search_results, meta={'keyword': keyword, 'location': location, 'offset': 0})

    def parse_search_results(self, response):
        location = response.meta['location']
        keyword = response.meta['keyword'] 
        offset = response.meta['offset'] 
        script_tag  = re.findall(r'window.mosaic.providerData\["mosaic-provider-jobcards"\]=(\{.+?\});', response.text)
        if script_tag is not None:
            json_blob = json.loads(script_tag[0])

            ## Extract Jobs From Search Page
            jobs_list = json_blob['metaData']['mosaicProviderJobCardsModel']['results']
            for index, job in enumerate(jobs_list):
                if job.get('jobkey') is not None:
                    job_url = 'https://vn.indeed.com/m/basecamp/viewjob?viewtype=embedded&jk=' + job.get('jobkey')
                    yield scrapy.Request(url=job_url, 
                            callback=self.parse_job, 
                            meta={
                                'keyword': keyword, 
                                'location': location, 
                                'page': round(offset / 10) + 1 if offset > 0 else 1,
                                'position': index,
                                'jobKey': job.get('jobkey'),
                            })

            
            # Paginate Through Jobs Pages
            if offset == 0:
                count_jobs_string = response.xpath('//div[@class = "jobsearch-JobCountAndSortPane-jobCount css-1af0d6o eu4oa1w0"]/span/text()').get()
                print(f'count job : {count_jobs_string}' )

                number_of_jobs = list(map(int, re.findall(r'\d+', count_jobs_string)))[0]
                jobs_per_page = 15

                for offset in range(10, (number_of_jobs // jobs_per_page ) * 10, 10):
                    url = self.get_indeed_search_url(keyword, location, offset)
                    yield scrapy.Request(url=url, callback=self.parse_search_results, meta={'keyword': keyword, 'location': location, 'offset': offset})
    
    def parse_job(self, response):
        location = response.meta['location']
        keyword = response.meta['keyword'] 
        page = response.meta['page'] 
        position = response.meta['position'] 
        script_tag  = re.findall(r"_initialData=(\{.+?\});", response.text)
        if script_tag is not None:
            json_blob = json.loads(script_tag[0])
            job = json_blob["jobInfoWrapperModel"]["jobInfoModel"]["jobInfoHeaderModel"]
            yield {
                'keyword': keyword,
                'location': location,
                'page': page,
                'position': position,
                'company': job.get('companyName'),
                'jobkey': response.meta['jobKey'],
                'jobTitle': job.get('jobTitle'),
                'jobDescription': json_blob["jobInfoWrapperModel"]["jobInfoModel"]["sanitizedJobDescription"],
            }




