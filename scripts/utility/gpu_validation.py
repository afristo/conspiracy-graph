import torch

# Test if the GPU on the machine is configured to use CUDA and is setup for pytorch
print(torch.cuda.is_available())  # Should return True if CUDA is available
print(torch.cuda.current_device())  # Get the ID of the current device
print(torch.cuda.get_device_name(torch.cuda.current_device()))  # Get GPU name
