package main

import (
	"io"
	"os"
	"fmt"
	"sync"
	"strconv"
	"net/url"
	"net/http"
	"io/ioutil"
	"github.com/lestrrat/go-libxml2"
)

type Request struct {
	url string
	header map[string]string
}

func (page Request) get_html() []byte {

	client := &http.Client{}
	req, _ := http.NewRequest("GET", page.url, nil)
	for key, value := range page.header {
		req.Header.Add(key, value)
	}

	res, _ := client.Do(req)
	body, _ := ioutil.ReadAll(res.Body)
	
	return body
}

func cates(body []byte) []string {

	doc, _ := libxml2.ParseHTML(body)
	defer doc.Free()

	nodes, _ := doc.Find("/html/body/div[2]/div[1]/ul/li/a/@href")

	cates := []string{}
	for index := range nodes.NodeList() {
		node := nodes.NodeList()[index]
		href := node.NodeValue()
		cates = append(cates, href)
	}

	return cates

}

func get_pages(body []byte) int {

	doc, _ := libxml2.ParseHTML(body)
	defer doc.Free()

	nodes, _ := doc.Find("/html/body/div[2]/div[4]/div/ul/li[last()-1]/span/a")
	pages, _ := strconv.Atoi(nodes.String())

	return pages

}

func download_file(file_name string, url string) {

	fmt.Println("downloading file: " + file_name)

	save_root := "./scels/"
    out, _ := os.Create(save_root+file_name)
    defer out.Close()

    resp, _ := http.Get(url)
    io.Copy(out, resp.Body)
}

func download_files(body []byte) {

	doc, _ := libxml2.ParseHTML(body)
	defer doc.Free()

	nodes, _ := doc.Find("/html/body/div[2]/div[3]/div/div[2]/div[2]/a/@href")

	for index := range nodes.NodeList() {
		node := nodes.NodeList()[index]
		file_url := node.NodeValue()
		parsed_url, _ := url.Parse(file_url)
		values := parsed_url.Query()
		file_name := values["name"][0]+".scel"
		download_file(file_name, file_url)
	}
}

func process_cate(request *Request) []string {

	cate_body := request.get_html()
	pages := get_pages(cate_body)

	page_urls := []string{}
	for page := 1; page <= pages; page ++ {
		page_url := request.url + "/default/" + strconv.Itoa(page)
		page_urls = append(page_urls, page_url)
	}

	return page_urls
}

func process_page(request Request) {

	page_body := request.get_html()
	download_files(page_body)
}

func main() {

	root := "https://pinyin.sogou.com"

	cates_page := "/dict/cate/index"
	cates_page_url := root + cates_page
	header := map[string]string {
		"Host": "pinyin.sogou.com", 
		"Connection": "keep-alive",
		"Cache-Control": "max-age=0",
		"Upgrade-Insecure-Requests": "1",
		"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36",
		"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
		"Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
	}
	cates_request := &Request{cates_page_url, header}
	cates_body := cates_request.get_html()
	cates := cates(cates_body)

	page_urls := []string{}
	for index := range cates {
		cate_page_url := root + cates[index]
		cate_request := &Request{cate_page_url, header}
		page_urls = append(page_urls, process_cate(cate_request)...)
	}

	wg := &sync.WaitGroup{}
	routine_guard := make(chan int, 50)
	for index := range page_urls {
		routine_guard <- 0

		wg.Add(1)
		go func(wg *sync.WaitGroup, url string, header map[string]string) {
			defer wg.Done()
			page_request := Request{url, header}
			process_page(page_request)
			<-routine_guard
        }(wg, page_urls[index], header)
	}

	wg.Wait()
}