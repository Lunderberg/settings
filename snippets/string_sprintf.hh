#ifndef _STRING_PRINTF_H
#define _STRING_PRINTF_H

#include <cstdio>
#include <cstdarg>
#include <string>

// std::string string_sprintf(const std::string& format, ...){
//   va_list arglist;
//   va_start(arglist, format);
//   const int len = vsnprintf(NULL,0,format.c_str(), arglist) + 1;
//   va_end(arglist);
//   char buf[len];
//   va_start(arglist,format);
//   vsnprintf(buf,len,format.c_str(),arglist);
//   va_end(arglist);
//   return buf;
// }

__attribute__((format (printf, 1, 2)))
std::string string_sprintf(const char* format, ...){
  static const int initial_buf_size = 100;
  va_list arglist;
  va_start(arglist, format);
  char buf[initial_buf_size];
  int len = vsnprintf(buf,initial_buf_size,format, arglist);
  va_end(arglist);

  if(len+1<initial_buf_size){
    return buf;
  } else if(len==-1){
    //VS2013 returns -1 for too long strings
    long buf_size = initial_buf_size;
    while(len==-1){
      buf_size *= 10;
      char long_buf[buf_size];
      va_start(arglist,format);
      len = vsnprintf(long_buf,buf_size,format,arglist);
      va_end(arglist);
      if(len>0){
	return long_buf;
      }
    }
  } else {
    char long_buf[len+1];
    va_start(arglist,format);
    vsnprintf(long_buf,len,format,arglist);
    va_end(arglist);
    return buf;
  }
}

#endif
