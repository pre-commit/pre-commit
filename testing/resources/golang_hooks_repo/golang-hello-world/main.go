package main


import (
	"fmt"
	"runtime"
	"github.com/BurntSushi/toml"
	"os"
)

type Config struct {
	What string
}

func main() {
	message := runtime.Version()
	if len(os.Args) > 1 {
		message = os.Args[1]
	}
	var conf Config
	toml.Decode("What = 'world'\n", &conf)
	fmt.Printf("hello %v from %s\n", conf.What, message)
}
